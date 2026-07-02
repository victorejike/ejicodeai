import pathlib, PyPDF2
p = pathlib.Path('ejicode-ai-platform-blueprint.pdf')
r = PyPDF2.PdfReader(str(p))
print('\n'.join(f'PAGE {i+1}\n{page.extract_text() or ""}' for i, page in enumerate(r.pages)))
