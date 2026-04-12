# Lights Out Solver

This project provides a comprehensive suite of tools and algorithms to solve the **Lights Out** puzzle. The puzzle is solved when all cells in a grid are set to `0`.

---

## Problem Description

**Lights Out** is a logic puzzle played on a grid of lights. When a cell is pressed, it and all its adjacent neighbors (up, down, left, right) toggle their state (from `1` to `0` or from `0` to `1`). The objective is to reach a state where all lights are turned off.

---

## List of Commands

### General Usage

The program follows a specific argument structure:

```bash
python main.py [ui_backend] [mode/algorithm] [file_name]
```

---

## 1. Launching the UI

* **Default (Pygame):**

  ```bash
  python main.py
  ```

* **Legacy (Tkinter):**

  ```bash
  python main.py tk
  ```

---

## 2. Solving a Specific Board

Run a specific algorithm on a board file (located in the `input/` directory):

* **Breadth-First Search (BFS):**

  ```bash
  python main.py bfs [board.txt]
  ```

* **Uniform Cost Search (UCS):**

  ```bash
  python main.py ucs [board.txt]
  ```

* **Greedy Search:**

  ```bash
  python main.py greedy [board.txt]
  ```

* **A* Search:**

  ```bash
  python main.py astar [board.txt]
  ```

* **Weighted A*:**

  ```bash
  python main.py wastar [board.txt]
  ```

* **GF(2) Mathematical Solver:**

  ```bash
  python main.py gf2 [board.txt]
  ```

---

## 3. Play Mode

To play the puzzle manually through the interface:

```bash
python main.py game [board.txt]
```

---

## Output and Reports

After running a solver, the program generates a report in the `output/` directory and prints a summary to the console:

* **Algorithm Details:** Displays the time taken, visited states, and board size.
* **Solution Path:** Provides the exact sequence of moves to solve the board.
* **File Export:** Saves results to a `.txt` file for later review.
