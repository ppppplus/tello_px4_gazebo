"""Native terminal scoreboard; no scoring decisions are made here."""

import curses
import unicodedata


def clock_text(seconds):
    tenths = max(0, int(float(seconds) * 10))
    minutes, remainder = divmod(tenths, 600)
    seconds, fraction = divmod(remainder, 10)
    return '%02d:%02d.%d' % (minutes, seconds, fraction)


def fit_text(text, width):
    """Truncate by terminal columns, including Chinese wide characters."""
    result, used = [], 0
    for char in str(text):
        if unicodedata.category(char).startswith('C'):
            char = ' '
        size = 2 if unicodedata.east_asian_width(char) in 'WF' else 1
        if used + size > width:
            break
        result.append(char)
        used += size
    return ''.join(result)


def event_text(event):
    kind, delta = event.get('kind'), event.get('score_delta', 0)
    if kind == 'round_started':
        return '新一轮就绪，等待起飞'
    if kind == 'takeoff':
        return '起飞成功，开始计时  +%d 分' % delta
    if kind == 'window':
        return '正确穿越红标窗  +%d 分' % delta
    if kind == 'landing':
        return '目标区降落成功，计时停止  +%d 分' % delta
    if kind == 'clock_reset':
        return '注意：仿真时钟发生回退'
    if kind == 'judge_message':
        message = str(event.get('message', '')).strip()
        if not event.get('accepted'):
            reasons = {
                'competition_not_running': '比赛尚未开始或已经结束',
                'ball_result_already_submitted': '球色已提交，不能重复',
                'wrong_lamp_order': '红点提交顺序错误',
                'too_far_from_lamp': '距离红点过远',
                'invalid_message': '消息格式错误',
            }
            reason = reasons.get(event.get('reason'), event.get('reason', '未知原因'))
            distance = ('，距离 %.3f m' % event['distance']) if 'distance' in event else ''
            return '拒绝 %s：%s%s' % (message, reason, distance)
        if event.get('reason') == 'ball_result_recorded':
            colors = {'r': '红', 'g': '绿', 'b': '蓝'}
            names = [colors.get(c, c) for c in message]
            return '识别提交 %s（旋转柜%s / 固定柜%s）+%d 分' % (
                message, names[0], names[1], delta)
        if event.get('reason') == 'lamp_confirmed':
            return '到达 %s 前，距离 %.3f m  +%d 分' % (
                message, event['distance'], delta)
    return str(kind or '未知事件')


def dashboard_rows(status, events, age):
    """Return a fixed header and chronological event lines for rendering/testing."""
    status = status or {}
    scores = status.get('scores', {})
    phase = {'ready': '等待起飞', 'running': '比赛进行中', 'finished': '比赛结束'}.get(
        status.get('phase'), '等待场景和裁判数据')
    header = [
        'TELLO 裁判机 | 实时计分',
        '轮次：%s    状态：%s' % (status.get('round_id', '--'), phase),
        '比赛计时：%s    总分：%3d / 100' % (
            clock_text(status.get('elapsed', 0)), status.get('score', 0)),
        '起飞 %2d/15 | 旋转柜 %2d/10 | 固定柜 %2d/10' % tuple(
            scores.get(k, 0) for k in ('takeoff', 'rotating_ball', 'fixed_ball')),
        '穿窗 %2d/20 | target1 %2d/10 | target2 %2d/10' % tuple(
            scores.get(k, 0) for k in ('window', 'lamp1', 'lamp2')),
        'target3 %2d/10 | 降落 %2d/15 | 红点进度 %d/3' % (
            scores.get('lamp3', 0), scores.get('landing', 0), status.get('lamp_progress', 0)),
        '计时使用仿真时间：起飞后开始，降落后冻结。',
        ('注意：位姿数据已中断 %.1f 秒，计时未推算！' % age) if age > 2 else '',
        '关键事件（按发生时间排列；上/下或 PgUp/PgDn 翻阅）',
    ]
    lines = ['[%s] %s' % (clock_text(e.get('elapsed', 0)), event_text(e)) for e in events]
    return header, lines


def run_dashboard(snapshot, is_shutdown):
    """Run in the judge process's real TTY, never as a video overlay."""
    def main(screen):
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        screen.timeout(100)
        scroll = 0
        while not is_shutdown():
            status, events, age = snapshot()
            header, lines = dashboard_rows(status, events, age)
            height, width = screen.getmaxyx()
            screen.erase()
            def put(row, value, style=0):
                if 0 <= row < height - 1:
                    try:
                        screen.addstr(row, 0, fit_text(value, max(0, width-1)), style)
                    except curses.error:
                        pass
            if height < 16 or width < 65:
                put(0, '请放大裁判终端（至少 65 列 × 16 行）')
            else:
                for row, value in enumerate(header):
                    put(row, value, curses.A_BOLD if row in (0, 2, 8) else 0)
                put(9, '-'*(width-1))
                capacity = height - 13
                scroll = min(scroll, max(0, len(lines)-capacity))
                end = len(lines)-scroll
                for row, line in enumerate(lines[max(0, end-capacity):end], 10):
                    put(row, line)
                put(height-3, '-'*(width-1))
                put(height-2, '共 %d 条事件 | %s | Q / Ctrl+C 退出裁判' % (
                    len(lines), '自动跟随最新事件' if scroll == 0 else '翻阅中，End 返回最新'))
            screen.refresh()
            key = screen.getch()
            if key in (ord('q'), ord('Q'), 3):
                break
            if key in (curses.KEY_UP, curses.KEY_PPAGE):
                scroll += 1 if key == curses.KEY_UP else 5
            elif key in (curses.KEY_DOWN, curses.KEY_NPAGE):
                scroll = max(0, scroll-(1 if key == curses.KEY_DOWN else 5))
            elif key == curses.KEY_END:
                scroll = 0
    curses.wrapper(main)
