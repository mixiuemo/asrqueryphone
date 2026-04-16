import os

class AI114Utils:
	def make_sure_dir_exists(dirName):
		if os.path.isdir(dirName)==False:
			os.makedirs(dirName) 