def application(environ, start_response):
    import sys
    output = f"Python version: {sys.version}\n"
    print(output.strip())
    start_response('200 OK', [('Content-type', 'text/plain; charset=utf-8')])
    return [output.encode('utf-8')]
