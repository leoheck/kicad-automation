#!/usr/bin/make

install_dependencies:
	sudo apt-get install -y kicad
	sudo apt-get install -y python3
	sudo apt-get install -y python3-pip
	sudo apt-get install -y xvfb
	sudo apt-get install -y recordmydesktop
	sudo apt-get install -y xdotool
	sudo apt-get install -y xclip

install_python_dependencies:
	sudo -H pip3 install xvfbwrapper
	sudo -H pip3 install argparse
	sudo -H pip3 install psutil
	sudo -H pip3 install PyPDF2
	sudo -H pip3 install junit-xml

install:
	sudo -H pip3 install .
