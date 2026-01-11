# CoDoc in MD

CoDoc in MD is a real-time collaborative Markdown editor built with [Reflex](https://reflex.dev/).
It combines a Monaco-powered writing experience with a live preview panel—so you can write, share,
and review Markdown docs in one place.

## Why CoDoc in MD

- **HackMD-friendly authoring**: Supports common HackMD-style fenced code options while keeping syntax highlighting.
    - Line numbers: `=`, `=101`, and continuation `=+`
    - Long-line wrapping: `!`
- **Reliable code rendering**: Code blocks are rendered with server-side highlighting (Pygments), so line numbers and
    highlighting remain stable even when fence options would otherwise confuse a Markdown parser.
- **Fast collaboration loop**: Share a link and co-edit immediately. Presence is shown with a lightweight session identity.
- **Writer-friendly preview**: Split / Editor-only / Preview-only modes make it easy to switch between writing and reading.
- **Clean, readable tables**: GitHub Flavored Markdown (GFM) tables render correctly and are styled to be pleasant to read.

## Key Features

- **Real-time collaboration**: Multiple users can edit the same document (currently backed by an in-memory store for demo/dev).
- **Monaco Editor for Markdown**: Solid editing UX with word wrap and code-editor ergonomics.
- **Live preview**: Markdown renders immediately as you type.
- **View modes**:
    - **Split**: Editor + preview side-by-side
    - **Editor**: Focused writing
    - **Preview**: Focused reading
- **Presence indicators**: Shows active collaborators with randomly generated display names and colors.

## Getting Started

This project uses [Poetry](https://python-poetry.org/) for dependency management.
Make sure you have **Python 3.11** and Poetry installed.

### 1) Clone

```bash
git clone <repository-url>
cd codoc_in_md
```

### 2) (Recommended) Ensure Poetry uses Python 3.11

Poetry may auto-select a different Python version (e.g. 3.12+). This project targets **3.11**.

```bash
poetry env use python3.11
poetry env info
```

If `python3.11` is not on your PATH, specify the full executable path:

```bash
poetry env use /absolute/path/to/python3.11
```

### 3) Install dependencies

```bash
poetry install
```

### 4) Run the app

```bash
poetry run reflex run
```

Then open:

- Frontend: http://localhost:3000
- Backend: http://localhost:8000

## Usage

1) **Create a new document**
     - Opening `/` auto-generates a document ID and redirects you.
     - You can also click **New Document** in the UI.

2) **Share and collaborate**
     - Copy the URL (it includes the `doc_id`) and share it.
     - Anyone opening the link joins the same doc and can edit in real time.

3) **Switch view modes**
     - Use **Split / Editor / Preview** to match your workflow.

## Tech Stack

- **Reflex**: Full-stack Python web framework
- **reflex-monaco**: Monaco Editor integration
- **Pygments**: Server-side syntax highlighting (used for HackMD-style code fences)
- **Python 3.11**
