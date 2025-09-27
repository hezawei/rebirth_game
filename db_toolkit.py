import psycopg2
from psycopg2 import sql
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.panel import Panel
from rich.text import Text
import os
import json
from datetime import datetime

# --- 数据库连接配置 ---
# 这些信息来自你的 docker-compose.yml 文件
DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "dbname": "rebirth",
    "user": "rebirth",
    "password": "StrongPass!"
}

# 初始化 rich console
console = Console()

def get_db_connection():
    """建立并返回一个数据库连接"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.OperationalError as e:
        console.print(f"[bold red]数据库连接失败！[/bold red]")
        console.print(f"错误信息: {e}")
        console.print("\n请确认:")
        console.print("1. Docker Desktop 是否已启动？")
        console.print("2. 是否已在项目目录下运行 'docker-compose up -d'？")
        return None

def show_stats():
    """显示数据库统计信息"""
    conn = get_db_connection()
    if not conn:
        return

    with conn.cursor() as cur:
        # 获取各表的统计数据
        cur.execute("SELECT COUNT(*) FROM users;")
        user_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM game_sessions;")
        session_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM story_nodes;")
        node_count = cur.fetchone()[0]
        
        # 获取最近的活动
        cur.execute("""
            SELECT created_at FROM users 
            ORDER BY created_at DESC LIMIT 1;
        """)
        latest_user = cur.fetchone()
        
        cur.execute("""
            SELECT created_at FROM game_sessions 
            ORDER BY created_at DESC LIMIT 1;
        """)
        latest_session = cur.fetchone()

        # 创建统计表格
        stats_table = Table(title="数据库统计信息")
        stats_table.add_column("项目", style="cyan")
        stats_table.add_column("数量/时间", style="magenta")
        
        stats_table.add_row("总用户数", str(user_count))
        stats_table.add_row("总游戏会话数", str(session_count))
        stats_table.add_row("总故事节点数", str(node_count))
        
        if latest_user:
            stats_table.add_row("最近注册用户", latest_user[0].strftime("%Y-%m-%d %H:%M:%S"))
        if latest_session:
            stats_table.add_row("最近游戏会话", latest_session[0].strftime("%Y-%m-%d %H:%M:%S"))
        
        console.print(stats_table)
    conn.close()


def format_datetime(dt: datetime) -> str:
    """格式化时间显示"""
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "-"


def select_user_interactively() -> dict | None:
    """引导用户从列表中选择一个用户"""
    console.print("[bold cyan]\n请选择用户，可输入关键字快速过滤 (直接回车列出全部)。[/bold cyan]")
    keyword = Prompt.ask("关键字 (Email 或 昵称)", default="").strip()

    conn = get_db_connection()
    if not conn:
        return None

    try:
        with conn.cursor() as cur:
            if keyword:
                like = f"%{keyword}%"
                cur.execute(
                    """
                    SELECT id, email, nickname, created_at
                    FROM users
                    WHERE email ILIKE %s OR COALESCE(nickname, '') ILIKE %s
                    ORDER BY created_at DESC;
                    """,
                    (like, like),
                )
            else:
                cur.execute(
                    """
                    SELECT id, email, nickname, created_at
                    FROM users
                    ORDER BY created_at DESC;
                    """
                )
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        console.print("[yellow]未找到符合条件的用户。[/yellow]")
        return None

    table = Table(title="请选择用户")
    table.add_column("序号", style="cyan", justify="right")
    table.add_column("Email", style="magenta")
    table.add_column("昵称", style="green")
    table.add_column("创建时间", style="yellow")

    for idx, row in enumerate(rows, start=1):
        table.add_row(str(idx), row[1], row[2] or "(未设置)", format_datetime(row[3]))

    console.print(table)
    console.print("输入序号选择用户，输入0返回上一层。")

    while True:
        selection = IntPrompt.ask("用户序号", default=0)
        if selection == 0:
            console.print("[green]已返回上一层。[/green]")
            return None
        if 1 <= selection <= len(rows):
            row = rows[selection - 1]
            return {
                "id": row[0],
                "email": row[1],
                "nickname": row[2],
                "created_at": row[3],
            }
        console.print("[red]序号超出范围，请重新输入。[/red]")


def select_session_interactively(
    *,
    user_id: str | None = None,
    prompt_title: str = "请选择游戏会话",
) -> dict | None:
    """引导用户从列表中选择一个游戏会话"""
    console.print(f"[bold cyan]\n{prompt_title}[/bold cyan]")

    keyword = ""
    if not user_id:
        keyword = Prompt.ask(
            "关键字 (用户Email或愿望，回车列出全部)",
            default="",
        ).strip()

    conn = get_db_connection()
    if not conn:
        return None

    try:
        with conn.cursor() as cur:
            base_query = (
                """
                SELECT gs.id, gs.wish, u.email, gs.created_at,
                       (SELECT COUNT(*) FROM story_nodes sn WHERE sn.session_id = gs.id) AS node_count
                FROM game_sessions gs
                JOIN users u ON gs.user_id = u.id
                """
            )
            where_clauses = []
            params: list = []

            if user_id:
                where_clauses.append("gs.user_id = %s")
                params.append(user_id)
            if keyword:
                like = f"%{keyword}%"
                where_clauses.append("(u.email ILIKE %s OR gs.wish ILIKE %s)")
                params.extend([like, like])

            if where_clauses:
                base_query += " WHERE " + " AND ".join(where_clauses)

            base_query += " ORDER BY gs.created_at DESC;"

            cur.execute(base_query, tuple(params))
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        console.print("[yellow]未找到符合条件的游戏会话。[/yellow]")
        return None

    table = Table(title="请选择游戏会话")
    table.add_column("序号", style="cyan", justify="right")
    table.add_column("会话ID", style="blue")
    table.add_column("初始愿望", style="magenta")
    table.add_column("用户Email", style="green")
    table.add_column("节点数", style="red", justify="right")
    table.add_column("创建时间", style="yellow")

    for idx, row in enumerate(rows, start=1):
        table.add_row(
            str(idx),
            str(row[0]),
            row[1],
            row[2],
            str(row[4]),
            format_datetime(row[3]),
        )

    console.print(table)
    console.print("输入序号选择会话，输入0返回上一层。")

    while True:
        selection = IntPrompt.ask("会话序号", default=0)
        if selection == 0:
            console.print("[green]已返回上一层。[/green]")
            return None
        if 1 <= selection <= len(rows):
            row = rows[selection - 1]
            return {
                "id": row[0],
                "wish": row[1],
                "email": row[2],
                "created_at": row[3],
                "node_count": row[4],
            }
        console.print("[red]序号超出范围，请重新输入。[/red]")


def select_story_node_interactively(session_id: int) -> dict | None:
    """引导用户从指定会话中选择一个故事节点"""
    conn = get_db_connection()
    if not conn:
        return None

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT sn.id, sn.parent_id, sn.story_text, sn.user_choice,
                       sn.created_at,
                       (SELECT COUNT(*) FROM story_nodes child WHERE child.parent_id = sn.id) AS child_count
                FROM story_nodes sn
                WHERE sn.session_id = %s
                ORDER BY sn.created_at ASC;
                """,
                (session_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        console.print("[yellow]该游戏会话暂时没有故事节点。[/yellow]")
        return None

    table = Table(title="请选择故事节点")
    table.add_column("序号", style="cyan", justify="right")
    table.add_column("节点ID", style="blue")
    table.add_column("父节点ID", style="blue")
    table.add_column("故事内容", style="green", max_width=40, overflow="fold")
    table.add_column("做出的选择", style="magenta")
    table.add_column("子节点数", style="red", justify="right")
    table.add_column("创建时间", style="yellow")

    for idx, row in enumerate(rows, start=1):
        table.add_row(
            str(idx),
            str(row[0]),
            str(row[1]) if row[1] else "(初始节点)",
            (row[2][:40] + "...") if len(row[2]) > 40 else row[2],
            row[3] or "N/A",
            str(row[5]),
            format_datetime(row[4]),
        )

    console.print(table)
    console.print("输入序号选择节点，输入0返回上一层。")

    while True:
        selection = IntPrompt.ask("节点序号", default=0)
        if selection == 0:
            console.print("[green]已返回上一层。[/green]")
            return None
        if 1 <= selection <= len(rows):
            row = rows[selection - 1]
            return {
                "id": row[0],
                "parent_id": row[1],
                "story_text": row[2],
                "user_choice": row[3],
                "created_at": row[4],
                "child_count": row[5],
            }
        console.print("[red]序号超出范围，请重新输入。[/red]")

def show_users():
    """查询并显示所有用户"""
    conn = get_db_connection()
    if not conn:
        return

    with conn.cursor() as cur:
        cur.execute("SELECT id, email, nickname, created_at FROM users ORDER BY created_at DESC;")
        rows = cur.fetchall()

        table = Table(title="所有用户")
        table.add_column("ID (UUID)", style="cyan", no_wrap=True)
        table.add_column("Email", style="magenta")
        table.add_column("昵称", style="green")
        table.add_column("创建时间", style="yellow")

        for row in rows:
            table.add_row(str(row[0]), row[1], row[2] or "(未设置)", format_datetime(row[3]))

        console.print(table)
    conn.close()


def show_game_sessions():
    """查询并显示所有游戏会话，并关联用户信息"""
    conn = get_db_connection()
    if not conn:
        return

    with conn.cursor() as cur:
        cur.execute("""
            SELECT gs.id, gs.wish, u.email, gs.created_at
            FROM game_sessions gs
            JOIN users u ON gs.user_id = u.id
            ORDER BY gs.created_at DESC;
        """)
        rows = cur.fetchall()

        table = Table(title="所有游戏会话")
        table.add_column("会话 ID", style="cyan")
        table.add_column("初始愿望", style="magenta")
        table.add_column("所属用户 (Email)", style="green")
        table.add_column("创建时间", style="yellow")

        for row in rows:
            table.add_row(str(row[0]), row[1], row[2], format_datetime(row[3]))

        console.print(table)
    conn.close()

def search_users():
    """搜索用户（按email或昵称）"""
    search_term = Prompt.ask("[bold yellow]请输入要搜索的Email或昵称[/bold yellow]")
    if not search_term:
        console.print("[red]搜索内容不能为空。[/red]")
        return

    conn = get_db_connection()
    if not conn:
        return

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, email, nickname, created_at 
            FROM users 
            WHERE email ILIKE %s OR nickname ILIKE %s
            ORDER BY created_at DESC;
        """, (f'%{search_term}%', f'%{search_term}%'))
        rows = cur.fetchall()

        if not rows:
            console.print(f"[yellow]未找到包含 '{search_term}' 的用户。[/yellow]")
            conn.close()
            return

        table = Table(title=f"搜索结果: '{search_term}'")
        table.add_column("ID (UUID)", style="cyan", no_wrap=True)
        table.add_column("Email", style="magenta")
        table.add_column("昵称", style="green")
        table.add_column("创建时间", style="yellow")

        for row in rows:
            table.add_row(str(row[0]), row[1], row[2], row[3].strftime("%Y-%m-%d %H:%M:%S"))

        console.print(table)
    conn.close()

def show_user_sessions():
    """显示特定用户的所有游戏会话"""
    user = select_user_interactively()
    if not user:
        return

    conn = get_db_connection()
    if not conn:
        return

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT gs.id, gs.wish, gs.created_at,
                   (SELECT COUNT(*) FROM story_nodes sn WHERE sn.session_id = gs.id) AS node_count
            FROM game_sessions gs
            WHERE gs.user_id = %s
            ORDER BY gs.created_at DESC;
            """,
            (user["id"],),
        )
        rows = cur.fetchall()

        if not rows:
            console.print(f"[yellow]用户 {user['email']} 没有游戏会话。[/yellow]")
            conn.close()
            return

        table = Table(title=f"用户 {user['email']} 的所有游戏会话")
        table.add_column("会话 ID", style="cyan")
        table.add_column("初始愿望", style="magenta")
        table.add_column("故事节点数", style="green")
        table.add_column("创建时间", style="yellow")

        for row in rows:
            table.add_row(str(row[0]), row[1], str(row[3]), format_datetime(row[2]))

        console.print(table)
    conn.close()

def show_story_nodes_for_session():
    """查询并显示某个游戏会话的所有故事节点"""
    session = select_session_interactively()
    if not session:
        return

    conn = get_db_connection()
    if not conn:
        return

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, parent_id, story_text, user_choice, choices, created_at
            FROM story_nodes
            WHERE session_id = %s
            ORDER BY created_at ASC;
            """,
            (session["id"],),
        )
        rows = cur.fetchall()

        if not rows:
            console.print(
                f"[yellow]会话 ID {session['id']} 还没有故事节点。[/yellow]"
            )
            conn.close()
            return

        console.print(
            f"[bold cyan]会话信息:[/bold cyan] 用户: {session['email']}, 愿望: {session['wish']}"
        )

        table = Table(title=f"会话 ID: {session['id']} 的故事线")
        table.add_column("节点 ID", style="cyan")
        table.add_column("父节点 ID", style="blue")
        table.add_column("故事内容", style="green", max_width=40)
        table.add_column("做出的选择", style="magenta")
        table.add_column("可选择数", style="red")
        table.add_column("创建时间", style="yellow")

        for row in rows:
            choices_list = json.loads(row[4]) if row[4] else []
            choice_count = len(choices_list)
            table.add_row(
                str(row[0]),
                str(row[1]) if row[1] else "(初始节点)",
                row[2][:40] + "..." if len(row[2]) > 40 else row[2],
                row[3] or "N/A",
                str(choice_count),
                format_datetime(row[5]),
            )

        console.print(table)
    conn.close()

def handle_query_menu():
    """处理查询子菜单"""
    while True:
        console.print("\n[bold cyan]-- 查询菜单 --[/bold cyan]")
        console.print("1. 查看所有用户")
        console.print("2. 搜索用户 (按Email/昵称)")
        console.print("3. 查看所有游戏会话")
        console.print("4. 查看某个用户的所有游戏会话")
        console.print("5. 查看某个会话的故事线")
        console.print("6. 查看数据库统计信息")
        console.print("7. 返回主菜单")
        choice = Prompt.ask("请选择", choices=["1", "2", "3", "4", "5", "6", "7"], default="7")

        if choice == '1':
            show_users()
        elif choice == '2':
            search_users()
        elif choice == '3':
            show_game_sessions()
        elif choice == '4':
            show_user_sessions()
        elif choice == '5':
            show_story_nodes_for_session()
        elif choice == '6':
            show_stats()
        elif choice == '7':
            break

def update_user_nickname():
    """修改用户昵称"""
    user = select_user_interactively()
    if not user:
        return

    conn = get_db_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cur:
            current_nickname = user["nickname"] or "(未设置)"
            console.print(f"当前昵称: [bold magenta]{current_nickname}[/bold magenta]")
            new_nickname = Prompt.ask("[bold yellow]请输入新昵称[/bold yellow]")

            if not new_nickname:
                console.print("[red]新昵称不能为空。[/red]")
                return

            cur.execute(
                "UPDATE users SET nickname = %s WHERE id = %s;",
                (new_nickname, user["id"]),
            )
            conn.commit()
            console.print(
                f"[bold green]用户 {user['email']} 的昵称已成功更新为: {new_nickname}[/bold green]"
            )

    except Exception as e:
        conn.rollback()
        console.print(f"[bold red]更新失败: {e}[/bold red]")
    finally:
        conn.close()


def update_session_wish():
    """修改游戏会话的愿望"""
    session = select_session_interactively()
    if not session:
        return

    conn = get_db_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cur:
            console.print(f"当前愿望: [bold magenta]{session['wish']}[/bold magenta]")
            console.print(f"所属用户: [bold cyan]{session['email']}[/bold cyan]")
            new_wish = Prompt.ask("[bold yellow]请输入新的愿望[/bold yellow]")

            if not new_wish:
                console.print("[red]新愿望不能为空。[/red]")
                return

            cur.execute(
                "UPDATE game_sessions SET wish = %s WHERE id = %s;",
                (new_wish, session["id"]),
            )
            conn.commit()
            console.print(
                f"[bold green]游戏会话 {session['id']} 的愿望已成功更新为: {new_wish}[/bold green]"
            )

    except Exception as e:
        conn.rollback()
        console.print(f"[bold red]更新失败: {e}[/bold red]")
    finally:
        conn.close()

def handle_update_menu():
    """处理修改子菜单"""
    while True:
        console.print("\n[bold yellow]-- 修改菜单 --[/bold yellow]")
        console.print("1. 修改用户昵称")
        console.print("2. 修改游戏会话的愿望")
        console.print("3. 返回主菜单")
        choice = Prompt.ask("请选择", choices=["1", "2", "3"], default="3")

        if choice == '1':
            update_user_nickname()
        elif choice == '2':
            update_session_wish()
        elif choice == '3':
            break

def delete_specific_session():
    """删除特定的游戏会话（及其所有故事节点）"""
    session = select_session_interactively(
        prompt_title="请选择要删除的游戏会话"
    )
    if not session:
        return

    console.print("将要删除的游戏会话信息:")
    console.print(f"- 会话ID: [bold cyan]{session['id']}[/bold cyan]")
    console.print(f"- 所属用户: [bold magenta]{session['email']}[/bold magenta]")
    console.print(f"- 初始愿望: [bold yellow]{session['wish']}[/bold yellow]")
    console.print(f"- 包含故事节点: [bold red]{session['node_count']}[/bold red] 个")

    if not Confirm.ask(
        "[bold red]确定要删除这个游戏会话吗？这将同时删除所有相关的故事节点！[/bold red]",
        default=False,
    ):
        console.print("[green]操作已取消。[/green]")
        return

    conn = get_db_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM game_sessions WHERE id = %s;", (session["id"],))
            conn.commit()
            console.print(
                f"[bold green]游戏会话 {session['id']} 及其所有故事节点已成功删除！[/bold green]"
            )

    except Exception as e:
        conn.rollback()
        console.print(f"[bold red]删除失败: {e}[/bold red]")
    finally:
        conn.close()

def delete_specific_story_node():
    """删除特定的故事节点（及其所有子节点）"""
    session = select_session_interactively(
        prompt_title="请选择包含目标故事节点的游戏会话"
    )
    if not session:
        return

    node = select_story_node_interactively(session["id"])
    if not node:
        return

    console.print("将要删除的故事节点信息:")
    console.print(f"- 节点ID: [bold cyan]{node['id']}[/bold cyan]")
    console.print(f"- 所属用户: [bold magenta]{session['email']}[/bold magenta]")
    console.print(f"- 所属会话: [bold yellow]{session['wish']}[/bold yellow]")
    console.print(
        f"- 故事内容: [bold yellow]{node['story_text'][:50]}{'...' if len(node['story_text']) > 50 else ''}[/bold yellow]"
    )
    console.print(f"- 做出的选择: [bold green]{node['user_choice'] or 'N/A'}[/bold green]")
    console.print(f"- 子节点数量: [bold red]{node['child_count']}[/bold red] 个")

    if node["child_count"] > 0:
        console.print("[bold red]注意：删除此节点将同时删除所有子节点（级联删除）！[/bold red]")

    if not Confirm.ask("[bold red]确定要删除这个故事节点吗？[/bold red]", default=False):
        console.print("[green]操作已取消。[/green]")
        return

    conn = get_db_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM story_nodes WHERE id = %s;", (node["id"],))
            conn.commit()
            console.print(
                f"[bold green]故事节点 {node['id']} 及其所有子节点已成功删除！[/bold green]"
            )

    except Exception as e:
        conn.rollback()
        console.print(f"[bold red]删除失败: {e}[/bold red]")
    finally:
        conn.close()

def delete_user_data():
    """根据用户 Email 删除用户及其所有相关数据"""
    user = select_user_interactively()
    if not user:
        return

    conn = get_db_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM game_sessions WHERE user_id = %s;",
                (user["id"],),
            )
            session_count = cur.fetchone()[0]

            cur.execute(
                """
                SELECT COUNT(*) FROM story_nodes sn
                JOIN game_sessions gs ON sn.session_id = gs.id
                WHERE gs.user_id = %s;
                """,
                (user["id"],),
            )
            node_count = cur.fetchone()[0]

            console.print("将要删除用户信息:")
            console.print(f"- Email: [bold magenta]{user['email']}[/bold magenta]")
            console.print(f"- 昵称: [bold cyan]{user['nickname'] or '(未设置)'}[/bold cyan]")
            console.print(f"- 用户ID: [bold yellow]{user['id']}[/bold yellow]")
            console.print(f"- 游戏会话数: [bold red]{session_count}[/bold red] 个")
            console.print(f"- 故事节点数: [bold red]{node_count}[/bold red] 个")

            if not Confirm.ask(
                "[bold red]这是一个不可逆操作，确定要删除这个用户及其所有数据吗？[/bold red]",
                default=False,
            ):
                console.print("[green]操作已取消。[/green]")
                return

            # 依次清理关联数据，避免外键约束阻塞
            cur.execute(
                """
                DELETE FROM story_nodes
                WHERE session_id IN (SELECT id FROM game_sessions WHERE user_id = %s);
                """,
                (user["id"],),
            )
            cur.execute("DELETE FROM game_sessions WHERE user_id = %s;", (user["id"],))
            cur.execute("DELETE FROM users WHERE id = %s;", (user["id"],))

            conn.commit()
            console.print(
                f"[bold green]用户 {user['email']} 及其所有数据已成功删除！[/bold green]"
            )

    except Exception as e:
        conn.rollback()
        console.print(f"[bold red]删除失败: {e}[/bold red]")
    finally:
        conn.close()

def truncate_all_data():
    """清空所有用户、游戏和故事数据"""
    console.print("[bold red]⚠️  警告：此操作将删除所有用户、所有游戏会话、所有故事节点！[/bold red]")
    console.print("这通常只在发布新版本或新一轮内测前执行。数据将无法恢复。")
    console.print("\n请输入 [bold yellow]'确认删除'[/bold yellow] 来继续:")
    
    confirm_text = Prompt.ask("").strip()
    if confirm_text != "确认删除":
        console.print("[green]✅ 操作已取消。[/green]")
        return
    
    if not Confirm.ask("[bold red]最后确认：你真的、真的确定要清空所有数据吗？[/bold red]", default=False):
        console.print("[green]✅ 操作已取消。[/green]")
        return

    conn = get_db_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cur:
            # 使用 TRUNCATE ... CASCADE 可以一次性清空所有关联表
            cur.execute(
                "TRUNCATE TABLE wish_moderation_records, story_saves, story_nodes, game_sessions, users RESTART IDENTITY CASCADE;"
            )
            conn.commit()
            console.print("\n[bold green]🎉 所有用户、游戏会话和故事节点数据已全部清空！数据库回到初始状态。[/bold green]")
    except Exception as e:
        conn.rollback()
        console.print(f"[bold red]❌ 操作失败: {e}[/bold red]")
    finally:
        conn.close()

def handle_delete_menu():
    """处理删除子菜单"""
    while True:
        console.print("\n[bold red]-- 删除/清空菜单 (危险操作) --[/bold red]")
        console.print("1. 删除指定用户 (及其所有数据)")
        console.print("2. 删除指定游戏会话 (及其所有故事节点)")
        console.print("3. 删除指定故事节点 (及其所有子节点)")
        console.print("4. [bold yellow]清空所有用户和游戏数据[/bold yellow] (重置数据库)")
        console.print("5. 返回主菜单")
        choice = Prompt.ask("请选择", choices=["1", "2", "3", "4", "5"], default="5")

        if choice == '1':
            delete_user_data()
        elif choice == '2':
            delete_specific_session()
        elif choice == '3':
            delete_specific_story_node()
        elif choice == '4':
            truncate_all_data()
        elif choice == '5':
            break

def main_menu():
    """显示主菜单并处理用户输入"""
    while True:
        console.print("\n" + "="*60)
        title = Text("PostgreSQL 数据库管理工具", style="bold green")
        console.print(Panel(title, expand=False))
        console.print("1. [cyan]📊 查询数据[/cyan]")
        console.print("2. [yellow]✏️  修改数据[/yellow]")
        console.print("3. [red]🗑️  删除/清空数据[/red]")
        console.print("4. [blue]🚪 退出[/blue]")
        console.print("\n[dim]💡 提示: 此工具提供了完整的数据库管理功能，包括精细化的查询、修改和删除操作。[/dim]")
        
        choice = Prompt.ask("请选择要执行的操作", choices=["1", "2", "3", "4"], default="4")

        if choice == '1':
            handle_query_menu()
        elif choice == '2':
            handle_update_menu()
        elif choice == '3':
            handle_delete_menu()
        elif choice == '4':
            console.print("\n[bold blue]👋 感谢使用数据库管理工具，再见！[/bold blue]")
            break

if __name__ == "__main__":
    main_menu()
