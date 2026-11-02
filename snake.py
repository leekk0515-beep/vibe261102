"""뱀 게임 (Snake Game) - tkinter 사용, 추가 설치 불필요

조작법:
  방향키 / WASD : 이동
  P 또는 Space  : 일시정지
  R             : 게임 오버 후 재시작
  Esc           : 종료
"""

import random
import tkinter as tk

# 설정
CELL = 20          # 한 칸 크기(px)
COLS = 30          # 가로 칸 수
ROWS = 25          # 세로 칸 수
START_SPEED = 120  # 시작 속도 (ms, 작을수록 빠름)
MIN_SPEED = 50     # 최대 속도 제한

BG_COLOR = "#1e1e1e"
SNAKE_HEAD = "#4caf50"
SNAKE_BODY = "#81c784"
FOOD_COLOR = "#ef5350"
TEXT_COLOR = "#ffffff"

DIRECTIONS = {
    "Up": (0, -1), "w": (0, -1), "W": (0, -1),
    "Down": (0, 1), "s": (0, 1), "S": (0, 1),
    "Left": (-1, 0), "a": (-1, 0), "A": (-1, 0),
    "Right": (1, 0), "d": (1, 0), "D": (1, 0),
}


class SnakeGame:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Snake Game")
        self.root.resizable(False, False)

        self.score_label = tk.Label(root, font=("Arial", 14, "bold"),
                                    bg=BG_COLOR, fg=TEXT_COLOR, anchor="w", padx=10)
        self.score_label.pack(fill="x")

        self.canvas = tk.Canvas(root, width=COLS * CELL, height=ROWS * CELL,
                                bg=BG_COLOR, highlightthickness=0)
        self.canvas.pack()

        root.bind("<Key>", self.on_key)
        self.high_score = 0
        self.after_id = None
        self.reset()

    def reset(self):
        cx, cy = COLS // 2, ROWS // 2
        self.snake = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.score = 0
        self.speed = START_SPEED
        self.running = True
        self.paused = False
        self.food = self.spawn_food()
        self.update_score()
        if self.after_id:
            self.root.after_cancel(self.after_id)
        self.tick()

    def spawn_food(self):
        free = [(x, y) for x in range(COLS) for y in range(ROWS)
                if (x, y) not in self.snake]
        return random.choice(free) if free else None

    def update_score(self):
        self.score_label.config(
            text=f"점수: {self.score}    최고 점수: {self.high_score}")

    def on_key(self, event):
        key = event.keysym
        if key == "Escape":
            self.root.destroy()
        elif key in ("r", "R") and not self.running:
            self.reset()
        elif key in ("p", "P", "space") and self.running:
            self.paused = not self.paused
            self.draw()
        elif key in DIRECTIONS:
            new_dir = DIRECTIONS[key]
            # 반대 방향으로는 바로 전환 불가
            if (new_dir[0] + self.direction[0], new_dir[1] + self.direction[1]) != (0, 0):
                self.next_direction = new_dir

    def tick(self):
        if self.running and not self.paused:
            self.step()
        self.draw()
        if self.running:
            self.after_id = self.root.after(self.speed, self.tick)

    def step(self):
        self.direction = self.next_direction
        hx, hy = self.snake[0]
        new_head = (hx + self.direction[0], hy + self.direction[1])

        will_eat = new_head == self.food
        # 먹지 않으면 꼬리가 빠지므로, 꼬리 칸으로 이동하는 것은 허용
        body = self.snake if will_eat else self.snake[:-1]

        if (not (0 <= new_head[0] < COLS and 0 <= new_head[1] < ROWS)
                or new_head in body):
            self.game_over()
            return

        self.snake.insert(0, new_head)
        if will_eat:
            self.score += 10
            self.high_score = max(self.high_score, self.score)
            self.speed = max(MIN_SPEED, self.speed - 3)
            self.update_score()
            self.food = self.spawn_food()
            if self.food is None:  # 판을 가득 채움
                self.game_over(win=True)
        else:
            self.snake.pop()

    def game_over(self, win=False):
        self.running = False
        self.win = win

    def draw(self):
        c = self.canvas
        c.delete("all")

        if self.food:
            fx, fy = self.food
            c.create_oval(fx * CELL + 2, fy * CELL + 2,
                          (fx + 1) * CELL - 2, (fy + 1) * CELL - 2,
                          fill=FOOD_COLOR, outline="")

        for i, (x, y) in enumerate(self.snake):
            c.create_rectangle(x * CELL + 1, y * CELL + 1,
                               (x + 1) * CELL - 1, (y + 1) * CELL - 1,
                               fill=SNAKE_HEAD if i == 0 else SNAKE_BODY,
                               outline="")

        w, h = COLS * CELL, ROWS * CELL
        if not self.running:
            msg = "축하합니다! 승리!" if getattr(self, "win", False) else "GAME OVER"
            c.create_text(w / 2, h / 2 - 20, text=msg,
                          fill=TEXT_COLOR, font=("Arial", 32, "bold"))
            c.create_text(w / 2, h / 2 + 20,
                          text=f"점수: {self.score}   |   R: 재시작   Esc: 종료",
                          fill=TEXT_COLOR, font=("Arial", 14))
        elif self.paused:
            c.create_text(w / 2, h / 2, text="일시정지 (P)",
                          fill=TEXT_COLOR, font=("Arial", 28, "bold"))


def main():
    root = tk.Tk()
    root.configure(bg=BG_COLOR)
    SnakeGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
