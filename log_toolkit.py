import subprocess
import sys
import shlex
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, IntPrompt
    from rich.text import Text
    HAS_RICH = True
except ModuleNotFoundError:
    HAS_RICH = False

    class Console:  # type: ignore[override]
        def print(self, *args, **kwargs):
            text = " ".join(str(arg) for arg in args)
            print(text)

    class Panel(str):  # type: ignore[override]
        def __new__(cls, content, title=None, subtitle=None, expand=False):
            lines = []
            if title:
                lines.append(f"[{title}]")
            lines.append(str(content))
            if subtitle:
                lines.append(f"({subtitle})")
            return str.__new__(cls, "\n".join(lines))

    class Prompt:  # type: ignore[override]
        @staticmethod
        def ask(prompt: str, choices=None, default=None):
            while True:
                suffix = f" [default: {default}]" if default is not None else ""
                response = input(f"{prompt}{suffix}: ").strip()
                if not response and default is not None:
                    response = default
                if choices and response not in choices:
                    print(f"请输入以下选项之一: {choices}")
                    continue
                return response

    class IntPrompt:  # type: ignore[override]
        @staticmethod
        def ask(prompt: str, default=None):
            while True:
                suffix = f" [default: {default}]" if default is not None else ""
                response = input(f"{prompt}{suffix}: ").strip()
                if not response and default is not None:
                    return default
                try:
                    return int(response)
                except ValueError:
                    print("请输入整数。")

    class Text(str):  # type: ignore[override]
        def __new__(cls, content, style=None):
            return str.__new__(cls, str(content))

COMPOSE_FILE = Path("deployment/configs/docker-compose.yml")
DEFAULT_TAIL_LINES = 200

console = Console()

if not HAS_RICH:
    console.print("提示: 未安装 rich 库，log_toolkit 正在使用简易文本模式运行。")


def run_compose_logs(service: str, *, tail: int = DEFAULT_TAIL_LINES, follow: bool = False, keyword: Optional[str] = None) -> None:
    """运行 docker compose logs 命令查看或跟随指定服务日志。"""
    if not COMPOSE_FILE.exists():
        console.print(f"[bold red]找不到 docker-compose 文件: {COMPOSE_FILE}[/bold red]")
        return

    cmd_parts = [
        "docker",
        "compose",
        "-f",
        str(COMPOSE_FILE),
        "logs",
    ]

    if follow:
        cmd_parts.append("-f")
    if tail:
        cmd_parts.extend(["--tail", str(tail)])

    cmd_parts.append(service)

    command = " ".join(shlex.quote(part) for part in cmd_parts)
    console.print(f"[cyan]$ {command}[/cyan]")

    try:
        if keyword and not follow:
            # pipe output through findstr/grep equivalent using Python filtering
            result = subprocess.run(cmd_parts, capture_output=True, text=True, check=False)
            if result.stdout:
                filtered = [line for line in result.stdout.splitlines() if keyword.lower() in line.lower()]
                if filtered:
                    for line in filtered:
                        console.print(line)
                else:
                    console.print(f"[yellow]未在日志中找到包含关键字 '{keyword}' 的行[/yellow]")
            if result.stderr:
                console.print(f"[red]{result.stderr}[/red]")
        else:
            # 直接将日志流量传给终端 (适用于跟随场景)
            subprocess.run(cmd_parts, check=False)
    except KeyboardInterrupt:
        console.print("\n[green]已停止跟随日志。[/green]")
    except FileNotFoundError:
        console.print("[bold red]未找到 docker/compose 命令，请确认 Docker 已安装并在 PATH 中。[/bold red]")
    except Exception as exc:  # pylint: disable=broad-except
        console.print(f"[bold red]执行日志命令时发生错误: {exc}[/bold red]")


def show_quick_commands() -> None:
    """展示常用的 docker compose 日志命令，方便复制。"""
    commands = [
        "docker compose -f deployment/configs/docker-compose.yml logs --tail 200 app",
        "docker compose -f deployment/configs/docker-compose.yml logs -f app",
        "docker compose -f deployment/configs/docker-compose.yml logs --tail 200 nginx",
        "docker compose -f deployment/configs/docker-compose.yml logs -f nginx",
        "docker compose -f deployment/configs/docker-compose.yml logs --tail 200 app | grep ERROR",
    ]

    panel = Panel("\n".join(commands), title="常用日志命令", subtitle="可直接复制粘贴使用")
    console.print(panel)


def main_menu() -> None:
    while True:
        console.print("\n" + "=" * 60)
        console.print(Panel(Text("Rebirth Game 日志工具", style="bold cyan"), expand=False))
        console.print("1. 查看后端(app)最近日志")
        console.print("2. 跟随后端(app)实时日志")
        console.print("3. 查看 Nginx 最近日志")
        console.print("4. 跟随 Nginx 实时日志")
        console.print("5. 按关键字过滤后端日志")
        console.print("6. 显示常用命令")
        console.print("7. 退出")

        choice = Prompt.ask("请选择操作", choices=["1", "2", "3", "4", "5", "6", "7"], default="7")

        if choice == "1":
            tail = IntPrompt.ask("显示最近多少行日志?", default=DEFAULT_TAIL_LINES)
            run_compose_logs("app", tail=tail)
        elif choice == "2":
            console.print("按 [bold magenta]Ctrl+C[/bold magenta] 可随时停止跟随日志。")
            run_compose_logs("app", follow=True, tail=0)
        elif choice == "3":
            tail = IntPrompt.ask("显示最近多少行日志?", default=DEFAULT_TAIL_LINES)
            run_compose_logs("nginx", tail=tail)
        elif choice == "4":
            console.print("按 [bold magenta]Ctrl+C[/bold magenta] 可随时停止跟随日志。")
            run_compose_logs("nginx", follow=True, tail=0)
        elif choice == "5":
            keyword = Prompt.ask("请输入要匹配的关键字").strip()
            if not keyword:
                console.print("[red]关键字不能为空。[/red]")
            else:
                tail = IntPrompt.ask("从最近多少行日志中搜索?", default=DEFAULT_TAIL_LINES)
                run_compose_logs("app", tail=tail, keyword=keyword)
        elif choice == "6":
            show_quick_commands()
        elif choice == "7":
            console.print("[green]感谢使用日志工具，再见！[/green]")
            break


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[green]已退出日志工具。[/green]")
        sys.exit(0)
