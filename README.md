# AntiGravity

**AntiGravity** is a native Swift 6 macOS workstation and front-end GUI designed for local LLM inference with [Ollama](https://ollama.com). It features deep reasoning stream parsing, real-time Mach/Metal memory telemetry, KV-cache optimization, and LaTeX/Markdown rendering.

---

## Highlights

* **Reasoning & Thinking Process Separation**: Built-in support for reasoning models (such as DeepSeek-R1, QwQ, and Qwen reasoning models). The internal thought process is cleanly isolated into an architectural collapsible disclosure box, while the final answer renders directly in the main conversation stream.
* **Stop-Safe Stateful Stream Parser**: Automatically recognizes native tags (`<think>`, `</think>`, `<｜end of thinking｜>`, `<|end_of_thought|>`), Ollama's structured `message.thinking` channel, and prefilled prompt templates.
* **Hardware & Memory Headroom Telemetry**: Inspects Metal GPU memory limits, unified RAM residency, and active KV-cache allocation in real time.
* **Tight-RAM Optimizer**: Presets for Q4_0 KV-cache quantization, Flash Attention, and adaptive context lengths.
* **Native Apple Silicon Build**: Compiled with Swift 6 for Apple Silicon Macs and packaged into a `.dmg` installer via GitHub Actions.

---

## Compiling & Downloading

This repository includes an automated GitHub Actions CI/CD workflow running on `macos-15`:

1. Every commit to `main` triggers `.github/workflows/build.yml`.
2. The workflow compiles the native release binary and packages `AntiGravity.app` into an Apple Silicon disk image installer (`.dmg`).
3. To download the compiled app, navigate to the **Actions** tab on GitHub, click on the latest workflow run, and download the **`AntiGravity-macOS-AppleSilicon-DMG`** artifact.

---

## Local Development & Manual Build

To build the project locally on an Apple Silicon Mac with Xcode command-line tools installed:

```bash
chmod +x motif_build_v12.txt
./motif_build_v12.txt
```

The compiled installer will be available under:
```
build/AntiGravity-1.0.0-macOS-arm64.dmg
```
