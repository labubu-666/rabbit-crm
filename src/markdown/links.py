import html as html_module


def repl_link_default(m):
    return f'<a href="{html_module.escape(m.group(2))}">{m.group(1)}</a>'
