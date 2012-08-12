from HTMLParser import HTMLParser
from htmlentitydefs import name2codepoint
import os
import re
from collections import deque


def word_wrap(text, width=80, prefix="", first_prefix=None, wrap_character="\n", extra_separators=[","]):
	text = re.sub(r"[\r\n]+", " ", text)
	first = True
	out = ""

	while(len(text) > width):
		i = width
		while (i > 0 and (text[i].isspace() == False and text[i] not in extra_separators)):
			i -= 1

		line = (first_prefix if first and first_prefix != None else prefix) + text[0:i]
		out += line + wrap_character
		text = text[i+1:]

		first = False

		if(i == 0):
			break

	if(len(text) > 0):
		out += (first_prefix if first and first_prefix != None else prefix) + text

	return out


class HtmlFormatOptions(object):
	"""docstring for HtmlFormatOptions"""
	def __init__(self):
		super(HtmlFormatOptions, self).__init__()

		self.indent_string = "\t"
		self.indent_count = 1
		self.newline = "\n"
		self.max_content_line_length = 80


class HtmlFormatter(HTMLParser):
	def __init__(self, output, opts=HtmlFormatOptions()):
		HTMLParser.__init__(self) # no idea why it has to be done like this
		self.opts = opts
		self.output_stream = output
		self.indent_level = 0
		self.re_whitespace_wrap = re.compile(r"^\s+$")

		self.ch_lookback = ""
		self.type_lookback = deque([])
		self.no_close = "meta".split(",")
	
	def push_type(self, tpl):
		if(len(self.type_lookback) > 50):
			self.type_lookback.popleft()

		self.type_lookback.append(tpl)

	def find_last_type_match(self, *args):
		i = 0
		largs = len(args)

		while(True):
			i += 1
			back = self.get_type_lookback(pos=i)
			
			if(back == None):
				return None
			
			if(largs <= len(back)):
				match = 0
				for idx in range(0, largs-1):
					match += 1 if args[idx] == None or args[idx] == back[idx] else 0
				if(match == largs-1):
					return (i, back)

	def get_type_lookback(self, pos=1):
		if(pos > len(self.type_lookback)):
			return None

		return self.type_lookback[-pos]

	def write(self, string):
		l = len(self.ch_lookback)
		lstr = len(string)
		if(l + lstr > 500):
			self.ch_lookback = self.ch_lookback[(l + lstr) - 550:]
		self.ch_lookback+=string
		self.output_stream.write(string)

	def clear_trailing_whitespace(self):
		"""clear all whitespace characters from the tail of the output stream's current position"""
		pre_pos = self.output_stream.tell()
		back = 1
		while(self.re_whitespace_wrap.match(self.ch_lookback[-back:])):
			back += 1

		if(back > 1): 
			self.ch_lookback = self.ch_lookback[:len(self.ch_lookback) - back + 1]
			self.output_stream.truncate(self.output_stream.tell() - back + 1) # get rid of the whitespace
			self.output_stream.seek(pre_pos - back + 1) # reset the output stream to the correct position

	def indent(self):
		self.indent_level += 1

	def outdent(self):
		self.indent_level -= 1

	def get_base_indent_string(self):
		return self.opts.indent_string * self.opts.indent_count

	def get_indent_string(self):
		return self.get_base_indent_string() * self.indent_level

	def write_newline(self):
		self.write("\n")
		self.write(self.get_indent_string())

	def write_single_space(self):
		self.write(" ")

	def write_tag(self, name, attrs):
		self.write(name)
		
		for attr in attrs:
			self.write_single_space()
			self.write(attr[0]) #attr name

			# write attr value if there is one
			if(len(attr) > 1 and attr[1] != None):
				self.write("=\"") # TODO: escape this to be safe?
				self.write(attr[1])
				self.write("\"")

	def handle_starttag(self, tag, attrs):
		nc = tag in self.no_close

		self.clear_trailing_whitespace()
		self.write_newline()
		self.write("<")
		self.write_tag(tag, attrs)
		
		if(nc):
			self.last_tag = (tag, "close")
			self.write(">")
			self.push_type(("tag", tag, "no_close"))
		else:
			self.last_tag = (tag, "open")
			self.write(">")
			self.indent()
			self.push_type(("tag", tag, "open"))
		
		self.write_newline()
	
	def handle_startendtag(self, tag, attrs):
		self.clear_trailing_whitespace()
		self.write_newline()
		self.write("<")
		self.write_tag(tag, attrs)
		self.write_single_space()
		self.write("/>")
		self.write_newline()
		self.push_type(("tag", tag, "self_close"))

	def handle_endtag(self, tag):
		self.clear_trailing_whitespace()
		self.outdent()

		last = self.get_type_lookback(pos=1)
		if(last == None or last[0] != "tag" or last[1] != tag or last[2] != "open"):
			self.write_newline()

		self.write("</")
		self.write(tag)
		self.write(">")
		self.write_newline()
		self.push_type(("tag", tag, "close"))
	
	def handle_data(self, data):
		if(data.isspace()):
			return

		ldata = len(data)

		self.clear_trailing_whitespace()
		self.write_newline()

		# find the last open tag of any type
		lmatch = self.find_last_type_match("tag", None, "open")
		if(lmatch != None and lmatch[1][1] not in ["script", "style"]):
			data = re.sub(r" {2,}|\t+", "", data)
			data = word_wrap(re.sub(r"^\s+|\s+$", "", data), prefix=self.get_indent_string(), first_prefix="", width=self.opts.max_content_line_length)

		self.write(data)
		self.push_type(("data", ldata))
	
	# TODO: add awesome comment formatting/word-wrap options
	def handle_comment(self, data):
		self.write("<!--")
		self.write_single_space()
		self.write(data)
		self.write_single_space()
		self.write("-->")
		self.write_newline()
		self.push_type(("comment", len(comment)))
	
	def handle_entityref(self, name):
		self.write("&")
		self.write(name)
		self.write(";")
		self.push_type(("entity_ref", name))
	
	def handle_charref(self, name):
		self.write("&#")
		self.write(name)
		self.write(";")
		self.push_type(("char_ref", name))	

	def handle_decl(self, data):
		self.write("<!")
		self.write(data)
		self.write(">")
		self.write_newline()
		self.push_type(("decl", len(data)))
