c = get_config()  # noqa

# Tell Jupyter to ignore heavy or duplicate files from being actively watched
c.ContentsManager.file_watcher_options = {
    "ignored_patterns": [
        "*.md",          # Ignores all MyST Markdown duplicates
        "*.lock",        # Ignores uv.lock
        "scripts/*",     # Ignores local setup scripts
        "skills/*",      # Ignores the AI workflow documentation
        ".git/*",
    ]
}
