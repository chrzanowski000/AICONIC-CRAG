# Research behind the design

This page lists the published work that shaped the pipeline, what we took from each idea, and
what we left out. Every source was checked on 2026-09-29. Numbers in square brackets point to the
list at the end. For the model choice (prices, scores, the chart) see [models.md](models.md).

## 1. When retrieved sources disagree

**Kinds of conflict.** A survey of knowledge conflicts [1] sorts them into three groups:
the model's memory vs the retrieved text (context-memory), retrieved texts vs each other
(inter-context), and the model's memory vs itself (intra-memory). Our demo is about the second
group: two documents in the corpus give different answers. We reduce the first group by telling
the LLM to use only the documents, because models tend to fall back on what they memorized when
a passage contradicts it [2].

**Models tend to hide conflicts.** Several studies show that plain RAG handles disagreeing
sources badly:

- Chen et al. [3] found that contradictions between sources change the model's confidence "only
  marginally". They proposed recalibrating models so they avoid giving any single answer when the
  evidence contains several conflicting answers.
- WikiContradict [7] (253 human-checked cases from Wikipedia) found that, given two passages with
  contradicting facts, all tested models struggled to write answers that reflect the conflict,
  most of all when the conflict is implicit.
- Wang et al. [5] set three goals for a model facing a conflict: notice it, point to the exact
  conflicting parts, and give the distinct answers. Models did well at noticing a conflict, but
  badly at the other two.
- RAMDocs [8] mixes ambiguity, misinformation and noise in the retrieved documents. A strong
  open model reached only 32.6 exact match. Their multi-agent debate method (MADAM-RAG) helped,
  but the authors say a large gap remains.
- CONFLICTS [9] lists five conflict types, each with its own correct behavior: no
  conflict (answer directly), complementary information (merge), conflicting opinions (show
  both views neutrally), outdated information (prefer the up-to-date one) and misinformation
  (ignore the bad source). Models often picked the wrong behavior. Asking them to reason about
  the conflict type first helped, but did not solve it.

**Models have biases when they choose.** Retrieval-augmented models tend to trust the answer that
appears more often ("majority rule") and the answer that matches their memory (confirmation
bias) [6]. Xie et al. [4] also found strong confirmation bias when the evidence is mixed. And
LLM rerankers prefer passages with newer dates even when the text is the same: across seven
models, adding fake recent dates moved the top-10 results forward by up to 4.78 years, and it
flipped pairwise choices between equally relevant passages in up to 25% of cases on average [10].

**What we took.**

- Outdated and disputed are **different cases** with different outputs, as in [9]. An outdated
  fact gets an answer plus a note; a dispute gets both versions and no answer.
- But we do not decide "outdated" from dates. In a company corpus, a newer Slack digest and an
  older HR handbook can simply disagree. Given the recency bias in [10], we only treat a document
  as outdated when the corpus says so: an explicit `supersedes` link. Everything else that
  disagrees is a dispute.
- Both versions are always shown, with id, source and date, which is what [3] and [5] ask for.
- Counting does not matter. One disagreeing pair is enough for a dispute, so "majority rule" [6]
  cannot hide the minority version.
- Since models are poor at noticing and presenting conflicts on their own [5, 7, 8, 9], we do
  not ask the writing model to present them. Detection is a separate step (`compare`, which can
  only answer same / different / unrelated and name the values), and the report is rendered by
  Python.

## 2. Corrective and self-checking RAG

Plain RAG [11] retrieves passages and generates from them, whether or not the passages are any
good. Two well-known designs add a check in between.

**Corrective RAG (CRAG)** [12] adds a small retrieval evaluator (a fine-tuned T5-large, 0.77B
parameters) that gives each document a score from -1 to 1. Two thresholds, set per dataset, pick
one of three actions: *Correct* (at least one document above the upper threshold: clean up the
documents and use them), *Incorrect* (all below the lower threshold: drop them and search the
web) or *Ambiguous* (do both).

**Self-RAG** [13] trains one model to emit "reflection tokens": `Retrieve` (is retrieval needed?),
`IsRel` (is this passage relevant?), `IsSup` (is the output supported by the passage?) and
`IsUse` (how useful is the answer, 1 to 5).

The LangGraph docs [14] show the same idea as a graph: a `grade_documents` step checks whether the
retrieved documents are relevant and a conditional edge sends the run to "answer" or "rewrite the
question".

**What we took.**

- A **retrieval gate** before any answer is written: first the similarity score cutoff, then a
  relevant yes/no per document from the `compare` step. This plays the role of CRAG's evaluator and
  Self-RAG's `IsRel`.
- **Thresholds in config**, as CRAG sets them per dataset (`SCORE_THRESHOLD`, `SCORE_MARGIN`).
- A **state graph with conditional edges** (LangGraph), so each route is explicit and traceable.
- A check after the answer, in the spirit of `IsSup`: citations must point to relevant, current
  documents, and a second LLM call looks for facts the claims do not support.

**What we did not take.**

- Web search on a failed retrieval. Our corpus is closed and made up; the web cannot know about
  Helios Dynamics, and a web page could not be cited as `[Dxx]`. We abstain instead.
- Training a critic model. No training budget, and a hosted model does the job (first Jev, now
  the LLM's `compare` step).
- A query rewrite loop. One pass is easier to test; it can be added later.

## 3. Saying "I don't know"

- SQuAD 2.0 [15] added unanswerable questions, so a reading system must also decide when not to
  answer.
- The RGB benchmark [16] tests four abilities RAG needs. One is "negative rejection": refusing
  when the retrieved documents do not contain the answer. LLMs struggled with it.
- A survey of abstention [17] looks at it from three sides: the question, the model and human
  values. A second study [18] found that a model's own calibration or self-reflection is not
  reliable for deciding when to abstain; having other models probe it worked better (up to 19.3%
  better abstain accuracy).
- Kalai et al. [19] argue that models guess because most tests score only right or wrong, so
  guessing pays. Their fix is to change the scoring, not to add more tests.
- Irrelevant retrieved text can make answers worse [20]. Filtering it helps, but a filter that is
  too strict also throws away useful passages.

**What we took.**

- Two gates (score cutoff, the LLM's relevance yes/no) and **Python decides** to abstain. No model is asked
  "do you know this?", which [18] suggests is unreliable.
- The "I don't know" output is built by code and lists the closest documents with their scores,
  so a cutoff that is too strict (the problem noted in [20]) is easy to spot.
- The eval gives credit for abstaining: the pets question (Q5) passes only when the system
  abstains with no citations. A disputed question passes only when there is no single answer.
  This follows the advice in [19].

## 4. Why the jobs are split between models and code

The pipeline gives each part one narrow job:

| part | job | can it write free text? |
|---|---|---|
| LLM (`openai/gpt-6-luna`) | extract one claim per document; compare claims (relevant yes/no; same / different / unrelated per pair, and what differs); write the final answer; check the answer | yes, but only in short, fixed places |
| Python rules | apply `supersedes` links, keep disputes between current documents, pick the route, render the dispute report, the outdated note and "I don't know" | not a model |

Until the `llm-judge` round a second model, Jev (`typesafe/jev-1.13`), decided relevance and
agree / disagree with probabilities, and a regex number check backed it up. Both were removed to
keep one model and one path (see `decisions.md` 6, 7 and 13). The findings below are why the
LLM's part is kept narrow.

Reasons:

- **LLM judges have known biases**: position, wordiness and self-preference, plus limited
  reasoning [21]. They also agree with people most of the time [21]. So the LLM only picks from
  fixed options on short claims, it never says which document is right, and the eval checks the
  result on every change.
- **A model that can write text can blur a conflict** into something like "about 12 to 16 weeks".
  So the comparison is a fixed choice plus one sentence that names both values, and the dispute
  report is built from the extracted claims by code. No step lets a model write a vague middle
  answer in place of the report.
- **Keep structured calls simple.** Strict output formats can lower a model's reasoning quality
  [22]. Each structured call does one small thing: copy facts, pick an option per pair, write
  short cited sentences, or list problems.
- **Compare short claims, not whole documents.** FActScore [23] checks text one small fact at a
  time, because a long passage often mixes supported and unsupported parts. We turn each document
  into one sentence, and `compare` works on those sentences.
- **Keep the context small.** Models use information in the middle of a long context less well
  [24]. We cap the context at 10 documents, and `compare` sees only short claims.
- **Do not trust model confidence.** Modern neural networks are often poorly calibrated [25], and
  model confidence barely reacts to conflicting evidence [3]. The pipeline therefore asks for no
  confidence at all: the LLM picks an option, Python applies fixed rules, and every decision is
  printed in the trace.

## 5. Options we looked at and did not use

| option | what it would add | why we left it out |
|---|---|---|
| Cross-encoder reranker [26] | better order of the top hits; rerankers do best on BEIR, at a high compute cost [27] | we have 40 short documents and already add every same-topic document after the search; a reranker reorders hits but cannot add the missing side of a conflict; one more model on CPU |
| BM25 or hybrid search [27, 28] | exact word matches; BM25 is a strong baseline [27] | the documents are short, with clear topics, and dense search plus the topic filter already finds both sides; hybrid adds a second index and score fusion to tune |
| NLI model for contradictions [29, 30] | a local contradiction score per sentence pair (a possible cheap second opinion next to the LLM) | it does not see the question, so it cannot say "unrelated"; NLI models tested on quantity reasoning did, on average, no better than always guessing the most common label [29], and most of our disputes are numbers; NLI filters can also drop useful passages [20]; one more model to install |
| Web search (as in CRAG [12]) | more sources when retrieval fails | closed, made-up corpus; web results cannot answer and cannot be cited as `[Dxx]`; we abstain instead |
| Let the LLM pick the "most recent" source | a single answer every time | a newer date does not prove a replacement; LLMs favor newer-looking text [10]; in our demo the newer document is on the "wrong" side on purpose (D04 vs D03, D06 vs D05) |
| Multi-agent debate (MADAM-RAG [8]) | several LLM rounds per question to sort out conflicts | many LLM calls per question and more randomness; one comparison call plus fixed rules gives the "show all valid answers" behavior we need |

To be fair to these options: NLI works well for inconsistency checks when it is applied sentence
by sentence [30], and a reranker or hybrid search would matter more in a large corpus. They are
the first things to try if the corpus grows. For embeddings we use `BAAI/bge-small-en-v1.5`, one
of the BGE models described in [31]: small (384 numbers per vector) and fast on CPU.

## 6. What this means for our design

| finding | part of the pipeline |
|---|---|
| Models hide conflicts or merge them [3, 5, 7, 8, 9] | `compare` marks each pair same / different / unrelated and names what differs; `conflict_report` (Python) prints both versions with id, source and creation date, and `answer` stays empty |
| Outdated and disputed need different outputs [9] | `reconcile` splits them: `outdated` list vs `disputes` list; different routes |
| Newer dates bias models [10] | only a `supersedes` link marks a document as outdated; the report says "a newer date alone does not settle it" |
| Majority and confirmation bias [4, 6] | one disagreeing pair is enough for a dispute; the LLM never picks a side |
| Check retrieval before answering [12, 13, 14] | score cutoff in `retrieve` + relevance gate in `reconcile`; conditional edges in the LangGraph graph |
| Abstaining is hard for LLMs [16, 18] | the abstain route is chosen by Python rules and rendered by code |
| Tests that reward guessing [19] | `eval.py` checks clean abstention (Q5) and "no single answer" for disputes (Q3, Q4) |
| LLM judges are biased [21] | the LLM only picks fixed options on short claims and never settles a dispute; Python decides; the eval checks every change |
| Structured output can hurt reasoning [22] | each structured call does one small job: extract claims, pick an option per pair, write a short answer, or list problems |
| Checking small facts is more precise [23] | `extract_claims` makes one short claim per document; `compare` compares claims; the answer check looks for single unsupported facts |
| Long contexts are used poorly [24] | at most 10 documents; `compare` sees short claims |
| Confidence may be off [25] | no confidence is used: fixed options, fixed rules, every decision printed in the trace |
| Retrieval can miss one side | `retrieve` adds every document with the same `topic` (a `supersedes` link never crosses topics) |

## Sources

1. Rongwu Xu, Zehan Qi, Zhijiang Guo, Cunxiang Wang, Hongru Wang, Yue Zhang, Wei Xu (2024). *Knowledge Conflicts for LLMs: A Survey.* <https://arxiv.org/abs/2403.08319>
2. Shayne Longpre, Kartik Perisetla, Anthony Chen, Nikhil Ramesh, Chris DuBois, Sameer Singh (2021). *Entity-Based Knowledge Conflicts in Question Answering.* EMNLP 2021. <https://arxiv.org/abs/2109.05052>
3. Hung-Ting Chen, Michael J. Q. Zhang, Eunsol Choi (2022). *Rich Knowledge Sources Bring Complex Knowledge Conflicts: Recalibrating Models to Reflect Conflicting Evidence.* EMNLP 2022. <https://arxiv.org/abs/2210.13701>
4. Jian Xie, Kai Zhang, Jiangjie Chen, Renze Lou, Yu Su (2023). *Adaptive Chameleon or Stubborn Sloth: Revealing the Behavior of Large Language Models in Knowledge Conflicts.* ICLR 2024. <https://arxiv.org/abs/2305.13300>
5. Yike Wang, Shangbin Feng, Heng Wang, Weijia Shi, Vidhisha Balachandran, Tianxing He, Yulia Tsvetkov (2023). *Resolving Knowledge Conflicts in Large Language Models.* COLM 2024. <https://arxiv.org/abs/2310.00935>
6. Zhuoran Jin, Pengfei Cao, Yubo Chen, Kang Liu, Xiaojian Jiang, Jiexin Xu, Qiuxia Li, Jun Zhao (2024). *Tug-of-War Between Knowledge: Exploring and Resolving Knowledge Conflicts in Retrieval-Augmented Language Models.* LREC-COLING 2024. <https://arxiv.org/abs/2402.14409>
7. Yufang Hou, Alessandra Pascale, Javier Carnerero-Cano, Tigran Tchrakian, Radu Marinescu, Elizabeth Daly, Inkit Padhi, Prasanna Sattigeri (2024). *WikiContradict: A Benchmark for Evaluating LLMs on Real-World Knowledge Conflicts from Wikipedia.* NeurIPS 2024 Datasets and Benchmarks. <https://arxiv.org/abs/2406.13805>
8. Han Wang, Archiki Prasad, Elias Stengel-Eskin, Mohit Bansal (2025). *Retrieval-Augmented Generation with Conflicting Evidence.* COLM 2025. <https://arxiv.org/abs/2504.13079>
9. Arie Cattan, Alon Jacovi, Ori Ram, Jonathan Herzig, Roee Aharoni, Sasha Goldshtein, Eran Ofek, Idan Szpektor, Avi Caciularu (2025). *DRAGged into Conflicts: Detecting and Addressing Conflicting Sources in Search-Augmented LLMs.* <https://arxiv.org/abs/2506.08500>
10. Hanpei Fang, Sijie Tao, Nuo Chen, Kai-Xin Chang, Tetsuya Sakai (2025). *Do Large Language Models Favor Recent Content? A Study on Recency Bias in LLM-Based Reranking.* SIGIR-AP 2025. <https://arxiv.org/abs/2509.11353>
11. Patrick Lewis, Ethan Perez, Aleksandra Piktus, Fabio Petroni, Vladimir Karpukhin, Naman Goyal, Heinrich Küttler, Mike Lewis, Wen-tau Yih, Tim Rocktäschel, Sebastian Riedel, Douwe Kiela (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* NeurIPS 2020. <https://arxiv.org/abs/2005.11401>
12. Shi-Qi Yan, Jia-Chen Gu, Yun Zhu, Zhen-Hua Ling (2024). *Corrective Retrieval Augmented Generation.* <https://arxiv.org/abs/2401.15884>
13. Akari Asai, Zeqiu Wu, Yizhong Wang, Avirup Sil, Hannaneh Hajishirzi (2023). *Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection.* <https://arxiv.org/abs/2310.11511>
14. LangChain docs. *Build a custom RAG agent with LangGraph* (the `grade_documents` step). <https://docs.langchain.com/oss/python/langgraph/agentic-rag>
15. Pranav Rajpurkar, Robin Jia, Percy Liang (2018). *Know What You Don't Know: Unanswerable Questions for SQuAD.* ACL 2018. <https://arxiv.org/abs/1806.03822>
16. Jiawei Chen, Hongyu Lin, Xianpei Han, Le Sun (2023). *Benchmarking Large Language Models in Retrieval-Augmented Generation.* AAAI 2024. <https://arxiv.org/abs/2309.01431>
17. Bingbing Wen, Jihan Yao, Shangbin Feng, Chenjun Xu, Yulia Tsvetkov, Bill Howe, Lucy Lu Wang (2024). *Know Your Limits: A Survey of Abstention in Large Language Models.* TACL. <https://arxiv.org/abs/2407.18418>
18. Shangbin Feng, Weijia Shi, Yike Wang, Wenxuan Ding, Vidhisha Balachandran, Yulia Tsvetkov (2024). *Don't Hallucinate, Abstain: Identifying LLM Knowledge Gaps via Multi-LLM Collaboration.* ACL 2024. <https://arxiv.org/abs/2402.00367>
19. Adam Tauman Kalai, Ofir Nachum, Santosh S. Vempala, Edwin Zhang (2025). *Why Language Models Hallucinate.* <https://arxiv.org/abs/2509.04664>
20. Ori Yoran, Tomer Wolfson, Ori Ram, Jonathan Berant (2023). *Making Retrieval-Augmented Language Models Robust to Irrelevant Context.* <https://arxiv.org/abs/2310.01558>
21. Lianmin Zheng, Wei-Lin Chiang, Ying Sheng, Siyuan Zhuang, Zhanghao Wu, Yonghao Zhuang, Zi Lin, Zhuohan Li, Dacheng Li, Eric P. Xing, Hao Zhang, Joseph E. Gonzalez, Ion Stoica (2023). *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena.* NeurIPS 2023 Datasets and Benchmarks. <https://arxiv.org/abs/2306.05685>
22. Zhi Rui Tam, Cheng-Kuang Wu, Yi-Lin Tsai, Chieh-Yen Lin, Hung-yi Lee, Yun-Nung Chen (2024). *Let Me Speak Freely? A Study on the Impact of Format Restrictions on Performance of Large Language Models.* <https://arxiv.org/abs/2408.02442>
23. Sewon Min, Kalpesh Krishna, Xinxi Lyu, Mike Lewis, Wen-tau Yih, Pang Wei Koh, Mohit Iyyer, Luke Zettlemoyer, Hannaneh Hajishirzi (2023). *FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation.* EMNLP 2023. <https://arxiv.org/abs/2305.14251>
24. Nelson F. Liu, Kevin Lin, John Hewitt, Ashwin Paranjape, Michele Bevilacqua, Fabio Petroni, Percy Liang (2023). *Lost in the Middle: How Language Models Use Long Contexts.* TACL. <https://arxiv.org/abs/2307.03172>
25. Chuan Guo, Geoff Pleiss, Yu Sun, Kilian Q. Weinberger (2017). *On Calibration of Modern Neural Networks.* ICML 2017. <https://arxiv.org/abs/1706.04599>
26. Rodrigo Nogueira, Kyunghyun Cho (2019). *Passage Re-ranking with BERT.* <https://arxiv.org/abs/1901.04085>
27. Nandan Thakur, Nils Reimers, Andreas Rücklé, Abhishek Srivastava, Iryna Gurevych (2021). *BEIR: A Heterogenous Benchmark for Zero-shot Evaluation of Information Retrieval Models.* NeurIPS 2021 Datasets and Benchmarks. <https://arxiv.org/abs/2104.08663>
28. Stephen Robertson, Hugo Zaragoza (2009). *The Probabilistic Relevance Framework: BM25 and Beyond.* Foundations and Trends in Information Retrieval 3(4). <https://doi.org/10.1561/1500000019>
29. Abhilasha Ravichander, Aakanksha Naik, Carolyn Rose, Eduard Hovy (2019). *EQUATE: A Benchmark Evaluation Framework for Quantitative Reasoning in Natural Language Inference.* CoNLL 2019. <https://arxiv.org/abs/1901.03735>
30. Philippe Laban, Tobias Schnabel, Paul N. Bennett, Marti A. Hearst (2021). *SummaC: Re-Visiting NLI-based Models for Inconsistency Detection in Summarization.* TACL. <https://arxiv.org/abs/2111.09525>
31. Shitao Xiao, Zheng Liu, Peitian Zhang, Niklas Muennighoff, Defu Lian, Jian-Yun Nie (2023). *C-Pack: Packed Resources For General Chinese Embeddings* (the technical report for the BGE embedding models). SIGIR 2024. <https://arxiv.org/abs/2309.07597>
