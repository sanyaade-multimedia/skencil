# -*- coding: utf-8 -*-
#
#	Copyright (C) 2011 by Igor E. Novikov 
#	
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#	
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#	
#	You should have received a copy of the GNU General Public License
#	along with this program.  If not, see <http://www.gnu.org/licenses/>. 

from skencil import modes

from controllers import AbstractController

class RectangleCreator(AbstractController):

	mode = modes.RECT_MODE

	def __init__(self, canvas, presenter):
		AbstractController.__init__(self, canvas, presenter)

	def do_action(self, event):
		if self.start and self.end:
			if abs(self.end[0] - self.start[0]) > 2 and \
			abs(self.end[1] - self.start[1]) > 2:
				rect = self.start + self.end
				self.presenter.api.create_rectangle(rect)
