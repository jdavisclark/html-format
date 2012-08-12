from __init__ import HtmlFormatter
import io
import re

sinput = open("./html.html", "r")
html = sinput.read()
sinput.close()

soutput = open("./sweet_code.html", "w")

formatter = HtmlFormatter(soutput)
formatter.feed(html)

soutput.close()