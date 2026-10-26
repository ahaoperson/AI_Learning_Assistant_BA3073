from __future__ import annotations

import json
from typing import Any, Callable

from backend.artifacts.filesystem import ArtifactRun
from backend.pipelines.authorship import add_author_credit
from backend.pipelines.common import (
    PipelineError,
    PipelineResult,
    extract_fenced_or_raw,
    format_citations,
    format_log,
)
from backend.pipelines.html_to_pdf import (
    A4_PAGE,
    ConvertError,
    HtmlToPdfConverter,
)
from backend.providers.base import (
    ModelProviderError,
    TextGenerationProvider,
    TextGenerationRequest,
)
from backend.timing import RunTimingRecorder, measure_stage


def run_essay_html_pipeline(
    *,
    artifact_run: ArtifactRun,
    model_profile: dict[str, Any],
    model_provider: TextGenerationProvider,
    pdf_converter: HtmlToPdfConverter,
    task_text: str,
    context_bundle: str,
    output_preference: str | None,
    options: dict[str, Any] | None,
    search: dict[str, Any],
    max_output_tokens: int,
    emit_event: Callable[[str, str], None] | None = None,
    timing: RunTimingRecorder | None = None,
) -> PipelineResult:
    log_lines = [
        "Pipeline: essay_html",
        f"Output preference: {output_preference or 'pdf'}",
        "Stage: generate_source",
    ]
    system_prompt, user_prompt = build_essay_html_prompt(
        task_text=task_text,
        context_bundle=context_bundle,
        options=options or {},
        search=search,
    )
    if emit_event:
        emit_event("generate_source", "Generating essay HTML source")

    try:
        with measure_stage(timing, "provider_generation"):
            raw_output = model_provider.generate_text(
                TextGenerationRequest(
                    profile=model_profile,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_output_tokens=max_output_tokens,
                    temperature=0.2,
                )
            )
    except ModelProviderError as exc:
        raise PipelineError(
            exc.code,
            exc.message,
            stage="generate_source",
            log_lines=log_lines,
        ) from exc
    except Exception as exc:
        raise PipelineError(
            "provider_unavailable",
            "The model provider request failed.",
            stage="generate_source",
            log_lines=log_lines,
        ) from exc

    source = extract_fenced_or_raw(raw_output, accepted_languages={"html", "htm"})
    source = add_author_credit(source.strip()) + "\n"
    html_path = artifact_run.write_output(
        "main.html",
        source,
        kind="source",
        media_type="text/html",
    )
    log_lines.extend(["Output: output/main.html", "Stage: convert_pdf"])
    if emit_event:
        emit_event("convert_pdf", "Converting essay HTML to PDF")

    pdf_path = artifact_run.run_dir / "output" / "main.pdf"
    try:
        with measure_stage(timing, "convert_pdf"):
            convert_result = pdf_converter.convert(
                html_path=html_path,
                pdf_path=pdf_path,
                page_config=A4_PAGE,
            )
    except ConvertError as exc:
        artifact_run.write_log("convert.log", exc.log_text)
        raise PipelineError(
            "convert_failed",
            exc.message,
            stage="convert_pdf",
            log_lines=log_lines,
        ) from exc
    except Exception as exc:
        artifact_run.write_log(
            "convert.log",
            "HTML-to-PDF converter raised an unexpected error.\n",
        )
        raise PipelineError(
            "convert_failed",
            "HTML-to-PDF conversion failed.",
            stage="convert_pdf",
            log_lines=log_lines,
        ) from exc

    artifact_run.write_log("convert.log", convert_result.log_text)
    artifact_run.write_output(
        "main.pdf",
        convert_result.pdf_path.read_bytes(),
        kind="pdf",
        media_type="application/pdf",
    )
    log_lines.extend(["Convert: pdf_ok", "Output: output/main.pdf"])
    return PipelineResult(log_text=format_log(log_lines))


def build_essay_html_prompt(
    *,
    task_text: str,
    context_bundle: str,
    options: dict[str, Any],
    search: dict[str, Any],
) -> tuple[str, str]:
    system_prompt = (
        "You are an expert teaching assistant writing complete academic essay and "
        "report deliverables as self-contained HTML documents. Return only the "
        "requested HTML source, with no surrounding explanation."
    )
    output_instruction = (
        "Return one complete self-contained HTML document. It must start with "
        "<!doctype html> and include <html>, <head>, and <body>. Include all CSS "
        "inside a <style> element: use a readable serif academic print layout, "
        "clear heading hierarchy, careful paragraph spacing, and CSS "
        "@page { size: A4; margin: 20mm; }. Do not use external stylesheet links, "
        "remote images, or remote HTTP(S) assets. If mathematical notation is "
        "needed, include inline KaTeX-compatible markup and any needed minimal "
        "KaTeX styling inline in the document; do not fetch KaTeX from a CDN at "
        "render time. Use inline SVG or CSS for diagrams. Cite any provided web "
        "sources in a References section using ordinary HTML. Do not wrap the "
        "answer in Markdown fences."
    )
    assignment_instruction = (
        "For the BA3073 'From AI Agent to Cloud Service' assignment, produce an "
        "evidence-based deployment report of no more than 20 A4 pages, including "
        "title, figures, references and appendices. Aim for 12–16 pages with "
        "readable typography; never hide content or shrink text to evade the limit. "
        "Use the requested language and only supplied student identity details. "
        "Organize it into: title and abstract; objectives and system architecture; "
        "Task 1 local Docker deployment and verification; explanation of the revised "
        "report-generation instructions; Task 2 Linux image build, ACR push/pull and "
        "ECS deployment; Task 3 DNS, Nginx, TLS and additional access control; "
        "verification results; security, persistence and cost analysis; limitations "
        "and prioritized improvements; conclusion and references. Explain FastAPI, "
        "the browser UI, SQLite, Qwen-compatible API, Docker image versus container, "
        "and host-mounted data/workspace directories in clear technical language. "
        "Explain the direct-IP test on port 14242 restricted to the student's public "
        "IP, followed by public ports 80/443 and closure of public port 14242 once "
        "Nginx forwards to 127.0.0.1:14242. Describe reverse-proxy access control "
        "separately from the built-in BNBU login. Describe API-key handling without "
        "revealing secrets, TLS renewal, backups including the encryption key, and "
        "ECS/storage/traffic/domain/model-token costs without inventing prices. "
        "Use only actual evidence supplied in the task and prepared context. Tie "
        "each result to its command, observed output, screenshot or log filename. "
        "Include local-ui-check.txt and ecs-docker-check.txt findings, screenshots "
        "of the working local and ECS interfaces with browser address bars, and the "
        "real HTTPS URL plus screenshot after the extra access-control check. "
        "Embed only supplied authentic screenshots, with legible address bars and "
        "captions; never draw simulated browser screenshots or fabricate logs, "
        "URLs, measurements, citations, deployment success, or student details. "
        "If evidence is absent, explicitly mark it 'Not yet verified / evidence "
        "required' and describe the report as a draft, not a completed assignment. "
        "Distinguish completed steps, failed checks and proposed improvements. "
        "Explain why each important configuration was chosen instead of merely "
        "listing commands. Use concise tables and inline architecture diagrams. "
        "Keep passwords, API keys, tokens and private keys out of every section. "
        "Preserve the AI Learning Assistant authorship credit."
    )
    user_prompt = "\n\n".join(
        [
            "[Assignment Task]\n" + task_text.strip(),
            "[Prepared Context]\n" + context_bundle.strip(),
            "[Search Citations]\n" + format_citations(search),
            "[Options]\n" + json.dumps(options, sort_keys=True),
            "[Output Contract]\n" + output_instruction,
            "[BA3073 Report Requirements]\n" + assignment_instruction,
        ]
    )
    return system_prompt, user_prompt
