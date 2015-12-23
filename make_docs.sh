#!/bin/sh

pandoc README.md -f markdown -t latex -s -o tex1.tex

xelatex tex1.tex
xelatex tex1.tex

#leave room for Biber if needed

xelatex tex1.tex
