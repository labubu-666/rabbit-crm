def repl_heading_default(m):
    level = len(m.group(1))
    content = m.group(2).strip()
    return f"<h{level}>{content}</h{level}>"
