from __future__ import annotations

from pathlib import Path


BUILD_INDEX = Path("build/web/index.html")


LOADER_CSS = """
        html, body {
            width: 100%;
            height: 100%;
            margin: 0;
            overflow: hidden;
            background: #111719;
        }

        body {
            display: flex;
            align-items: center;
            justify-content: center;
        }

        canvas.emscripten {
            image-rendering: pixelated;
            image-rendering: crisp-edges;
            max-width: 100vw;
            max-height: 100vh;
        }

        #status {
            position: fixed;
            left: 50%;
            top: 50%;
            z-index: 10;
            width: min(420px, calc(100vw - 40px));
            padding: 24px 26px;
            transform: translate(-50%, -50%);
            border: 1px solid #5c675f;
            background: rgba(15, 20, 22, 0.94);
            color: #e8e4d6;
            font: 700 16px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            text-align: center;
            letter-spacing: 0;
            box-shadow: 0 22px 60px rgba(0, 0, 0, 0.42);
        }

        #status::before {
            content: "Dead Streets";
            display: block;
            margin-bottom: 8px;
            color: #d6bc79;
            font-size: 24px;
        }

        #progress, progress {
            width: min(360px, calc(100vw - 80px));
            height: 8px;
            margin-top: 18px;
            accent-color: #d6bc79;
        }
"""


LOADER_JS = """
    <script>
    (() => {
        const translations = [
            [/Downloading/i, "Carregando arquivos"],
            [/Preparing/i, "Preparando o jogo"],
            [/Running/i, "Iniciando"],
            [/Starting/i, "Iniciando"],
            [/Loading/i, "Carregando"],
        ];

        const translateStatus = () => {
            const status = document.getElementById("status");
            if (!status || !status.textContent.trim()) return;
            for (const [pattern, label] of translations) {
                if (pattern.test(status.textContent)) {
                    status.textContent = label + "...";
                    return;
                }
            }
        };

        const fitCanvas = () => {
            const canvas = document.getElementById("canvas");
            if (!canvas) return;
            canvas.style.maxWidth = "100vw";
            canvas.style.maxHeight = "100vh";
            canvas.style.objectFit = "contain";
        };

        new MutationObserver(() => {
            translateStatus();
            fitCanvas();
        }).observe(document.documentElement, { childList: true, subtree: true, characterData: true });

        window.addEventListener("resize", fitCanvas);
        window.addEventListener("load", () => {
            translateStatus();
            fitCanvas();
        });
        translateStatus();
    })();
    </script>
"""


def main() -> None:
    if not BUILD_INDEX.exists():
        raise SystemExit(f"Arquivo nao encontrado: {BUILD_INDEX}")

    html = BUILD_INDEX.read_text(encoding="utf-8")
    html = html.replace('<html lang="en-us">', '<html lang="pt-BR">')
    html = html.replace("Downloading...", "Carregando arquivos...")

    if "<title>" in html:
        html = html.replace("<title>pygame-wasm</title>", "<title>Dead Streets</title>")
    else:
        html = html.replace("<head>", "<head><title>Dead Streets</title>", 1)

    if "#status::before" not in html:
        html = html.replace("</style>", f"{LOADER_CSS}\n    </style>", 1)

    if "const translations = [" not in html:
        if "</body>" in html:
            html = html.replace("</body>", f"{LOADER_JS}\n</body>", 1)
        else:
            html = html.replace("</html>", f"{LOADER_JS}\n</html>", 1)

    BUILD_INDEX.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
