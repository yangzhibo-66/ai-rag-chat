"""RAG 检索质量评估脚本（轻量版，无额外依赖）。

用法（在 backend 目录、激活 venv 后运行）：

    # 1. 准备测试集 rag_eval_cases.json：
    # [
    #   {"question": "PDF 扫描页是怎么处理的？",
    #    "expected_keywords": ["OCR", "扫描"],
    #    "document_ids": [1, 2]}          # document_ids 可省略，默认全部已完成文档
    # ]
    #
    # 2. 运行：
    python tools/rag_eval.py --user-id 1 --cases rag_eval_cases.json --top-k 5
    # 加 --answer 会额外调用 LLM 生成答案（较慢、消耗 token）

指标说明：
    hit_rate@k：top-k 结果中至少出现一个 expected_keywords 的问题占比
    avg_similarity：命中结果的平均语义相似度
    每个问题会打印命中的来源（文件名/页码/小节），便于人工核对可追溯性。

若需要 RAGAS 指标（Context Precision / Faithfulness / Answer Relevancy），
可在同一虚拟环境 `pip install ragas datasets` 后，把本脚本收集的
(contexts, question, answer) 三元组接入 ragas.evaluate()。
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings  # noqa: E402
from database import SessionLocal  # noqa: E402
from models import Document  # noqa: E402
from services import retrieval  # noqa: E402


def load_cases(path: str) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("测试集必须是 JSON 数组")
    for i, case in enumerate(data):
        if "question" not in case:
            raise ValueError(f"第 {i} 条用例缺少 question 字段")
    return data


def evaluate_retrieval(user_id: int, cases: list[dict], top_k: int) -> dict:
    db = SessionLocal()
    try:
        completed_ids = {
            d.id
            for d in db.query(Document.id)
            .filter(Document.user_id == user_id, Document.status == "completed")
            .all()
        }
    finally:
        db.close()

    hit_count = 0
    sim_sum, sim_n = 0.0, 0
    report = []

    for case in cases:
        question = case["question"]
        keywords = [k.lower() for k in case.get("expected_keywords", [])]
        doc_ids = case.get("document_ids")
        if doc_ids:
            doc_ids = [d for d in doc_ids if d in completed_ids]

        hits = retrieval.search(user_id, question, document_ids=doc_ids or None, top_k=top_k)

        joined = " ".join(h["content"] for h in hits).lower()
        matched = [k for k in keywords if k in joined]
        hit = (not keywords) or bool(matched)
        hit_count += int(hit)

        sims = [h["similarity"] for h in hits if h.get("similarity") is not None]
        sim_sum += sum(sims)
        sim_n += len(sims)

        report.append(
            {
                "question": question,
                "hit": hit,
                "matched_keywords": matched,
                "sources": [
                    {
                        "filename": h.get("filename"),
                        "page": h.get("page_number"),
                        "section": h.get("section"),
                        "similarity": h.get("similarity"),
                    }
                    for h in hits
                ],
            }
        )

    return {
        "hit_rate": hit_count / len(cases) if cases else 0.0,
        "avg_similarity": (sim_sum / sim_n) if sim_n else 0.0,
        "report": report,
    }


async def generate_answers(user_id: int, report: list[dict], cases: list[dict]) -> None:
    from services.ai_service import stream_response, _build_context

    # 重新检索拿完整 chunk 内容（report 里只有来源摘要）
    for case, item in zip(cases, report):
        db = SessionLocal()
        try:
            hits = retrieval.search(user_id, case["question"], document_ids=case.get("document_ids"))
        finally:
            db.close()
        answer = ""
        async for token in stream_response(case["question"], hits, [], chat_mode="rag_selected"):
            answer += token
        item["answer"] = answer
        print(f"\nQ: {case['question']}\nA: {answer[:500]}{'...' if len(answer) > 500 else ''}")


def main():
    parser = argparse.ArgumentParser(description="RAG 检索质量评估")
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--cases", default="rag_eval_cases.json")
    parser.add_argument("--top-k", type=int, default=settings.RAG_TOP_K)
    parser.add_argument("--answer", action="store_true", help="同时调用 LLM 生成答案")
    args = parser.parse_args()

    cases = load_cases(args.cases)
    result = evaluate_retrieval(args.user_id, cases, args.top_k)

    print(f"用例数: {len(cases)}  hit_rate@{args.top_k}: {result['hit_rate']:.2%}  "
          f"avg_similarity: {result['avg_similarity']:.3f}")
    for item in result["report"]:
        mark = "✓" if item["hit"] else "✗"
        print(f"\n[{mark}] {item['question']}")
        for s in item["sources"]:
            print(f"    - {s['filename']} 第{s['page']}页 {s['section'] or ''} (sim={s['similarity']})")

    if args.answer:
        asyncio.run(generate_answers(args.user_id, result["report"], cases))

    out_path = Path("rag_eval_report.json")
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n详细报告已写入 {out_path.resolve()}")


if __name__ == "__main__":
    main()
