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

from copy import deepcopy

from uc2.sk1doc import model
from uc2 import uc_conf, libcairo

from skencil import _, config
from skencil import events



class PresenterAPI:

	presenter = None
	view = None
	methods = None
	model = None
	app = None
	eventloop = None
	undo = []
	redo = []
	undo_marked = False
	selection = None

	def __init__(self, presenter):
		self.presenter = presenter
		self.selection = presenter.selection
		self.methods = self.presenter.methods
		self.model = presenter.model
		self.view = presenter.canvas

		self.eventloop = presenter.eventloop
		self.app = presenter.app
		self.undo = []
		self.redo = []

	def do_undo(self):
		transaction_list = self.undo[-1][0]
		for transaction in transaction_list:
			self._do_action(transaction)
		tr = self.undo[-1]
		self.undo.remove(tr)
		self.redo.append(tr)
		self.eventloop.emit(self.eventloop.DOC_MODIFIED)
		if self.undo and self.undo[-1][2]:
			self.presenter.reflect_saving()
		if not self.undo and not self.undo_marked:
			self.presenter.reflect_saving()

	def do_redo(self):
		transaction_list = self.redo[-1][1]
		for transaction in transaction_list:
			self._do_action(transaction)
		tr = self.redo[-1]
		self.redo.remove(tr)
		self.undo.append(tr)
		self.eventloop.emit(self.eventloop.DOC_MODIFIED)
		if not self.undo or self.undo[-1][2]:
			self.presenter.reflect_saving()

	def _do_action(self, action):
		if not action: return
		if len(action) == 1:
			action[0]()
		elif len(action) == 2:
			action[0](action[1])
		elif len(action) == 3:
			action[0](action[1], action[2])
		elif len(action) == 4:
			action[0](action[1], action[2], action[3])
		elif len(action) == 5:
			action[0](action[1], action[2], action[3], action[4])
		elif len(action) == 6:
			action[0](action[1], action[2], action[3], action[4], action[5])

	def add_undo(self, transaction):
		self.redo = []
		self.undo.append(transaction)
		self.eventloop.emit(self.eventloop.DOC_MODIFIED)

	def save_mark(self):
		for item in self.undo:
			item[2] = False
		for item in self.redo:
			item[2] = False

		if self.undo:
			self.undo[-1][2] = True
			self.undo_marked = True

	def clear_history(self):
		self.undo = []
		self.redo = []
		events.emit(events.DOC_MODIFIED, self.presenter)
		self.presenter.reflect_saving()

	def set_doc_origin(self, origin):
		cur_origin = self.model.doc_origin
		transaction = [
			[[self.methods.set_doc_origin, cur_origin]],
			[[self.methods.set_doc_origin, origin]],
			False]
		self.methods.set_doc_origin(origin)
		self.add_undo(transaction)

	def _delete_object(self, obj):
		self.methods.delete_object(obj)
		if obj in self.selection.objs:
			self.selection.remove([obj])

	def _insert_object(self, obj, parent, index):
		self.methods.insert_object(obj, parent, index)

	def insert_object(self, obj, parent, index):
		self._insert_object(obj, parent, index)
		transaction = [
			[[self._delete_object, obj]],
			[[self._insert_object, obj, parent, index]],
			False]
		self.add_undo(transaction)

	def delete_object(self, obj, parent, index):
		self._delete_object(obj)
		transaction = [
			[[self._insert_object, obj, parent, index]],
			[[self._delete_object, obj]],
			False]
		self.add_undo(transaction)

	def _get_layers_snapshot(self):
		layers_snapshot = []
		model = self.presenter.model
		page = self.presenter.active_page
		layers = page.childs + model.childs[1].childs
		for layer in layers:
			layers_snapshot.append([layer, [] + layer.childs])
		return layers_snapshot

	def _set_layers_snapshot(self, layers_snapshot):
		for layer, childs in layers_snapshot:
			layer.childs = childs

	def _delete_objects(self, objs_list):
		for obj, parent, index in objs_list:
			self.methods.delete_object(obj)
			if obj in self.selection.objs:
				self.selection.remove([obj])

	def _insert_objects(self, objs_list):
		for obj, parent, index in objs_list:
			self.methods.insert_object(obj, parent, index)

	def insert_objects(self, objs_list):
		self._insert_objects(objs_list)
		transaction = [
			[[self._delete_objects, objs_list]],
			[[self._insert_objects, objs_list]],
			False]
		self.add_undo(transaction)

	def delete_objects(self, objs_list):
		self._delete_objects(objs_list)
		transaction = [
			[[self._insert_objects, objs_list]],
			[[self._delete_objects, objs_list]],
			False]
		self.add_undo(transaction)

	def delete_selected(self):
		if self.selection.objs:
			before = self._get_layers_snapshot()
			for obj in self.selection.objs:
				self.methods.delete_object(obj)
			after = self._get_layers_snapshot()

			transaction = [
				[[self._set_layers_snapshot, before]],
				[[self._set_layers_snapshot, after]],
				False]
			self.add_undo(transaction)
		self.selection.clear()

	def cut_selected(self):
		self.copy_selected()
		self.delete_selected()

	def copy_selected(self):
		if self.selection.objs:
			self.app.clipboard.set(self.selection.objs)

	def paste_selected(self):
		objs = self.app.clipboard.get()
		before = self._get_layers_snapshot()
		self.methods.append_objects(objs, self.presenter.active_layer)
		after = self._get_layers_snapshot()
		transaction = [
			[[self._set_layers_snapshot, before]],
			[[self._set_layers_snapshot, after]],
			False]
		self.add_undo(transaction)
		self.selection.set(objs)


	def _normalize_rect(self, rect):
		x0, y0, x1, y1 = rect
		x0, y0 = self.view.win_to_doc([x0, y0])
		x1, y1 = self.view.win_to_doc([x1, y1])
		new_rect = [0, 0, 0, 0]
		if x0 < x1:
			new_rect[0] = x0
			new_rect[2] = x1 - x0
		else:
			new_rect[0] = x1
			new_rect[2] = x0 - x1
		if y0 < y1:
			new_rect[1] = y0
			new_rect[3] = y1 - y0
		else:
			new_rect[1] = y1
			new_rect[3] = y0 - y1
		return new_rect

	def create_rectangle(self, rect):
		rect = self._normalize_rect(rect)
		parent = self.presenter.active_layer
		obj = model.Rectangle(config, parent, rect)
		style = deepcopy(self.model.styles['Default Style'])
		obj.style = style
		obj.update()
		index = len(parent.childs)
		self.insert_object(obj, parent, index)
		self.selection.set([obj])

	def _get_objs_styles(self, objs):
		result = []
		for obj in objs:
			style = deepcopy(obj.style)
			result.append([obj, style])
		return result

	def _set_objs_styles(self, objs_styles):
		for obj, style in objs_styles:
			obj.style = style

	def _fill_objs(self, objs, color):
		for obj in objs:
			style = deepcopy(obj.style)
			if color:
				fill = style[0]
				new_fill = []
				if not fill:
					new_fill.append(config.default_fill_rule)
				else:
					new_fill.append(fill[0])
				new_fill.append(uc_conf.FILL_SOLID)
				new_fill.append(deepcopy(color))
				style[0] = new_fill
			else:
				style[0] = []
			obj.style = style

	def fill_selected(self, color):
		if self.selection.objs:
			color = deepcopy(color)
			objs = [] + self.selection.objs
			initial_styles = self._get_objs_styles(objs)
			self._fill_objs(objs, color)
			transaction = [
				[[self._set_objs_styles, initial_styles]],
				[[self._fill_objs, objs, color]],
				False]
			self.add_undo(transaction)

	def _stroke_objs(self, objs, color):
		for obj in objs:
			style = deepcopy(obj.style)
			if color:
				stroke = style[1]
				if not stroke:
					new_stroke = deepcopy(config.default_stroke)
				else:
					new_stroke = deepcopy(stroke)
				new_stroke[2] = deepcopy(color)
				style[1] = new_stroke
			else:
				style[1] = []
			obj.style = style

	def stroke_selected(self, color):
		if self.selection.objs:
			color = deepcopy(color)
			objs = [] + self.selection.objs
			initial_styles = self._get_objs_styles(objs)
			self._stroke_objs(objs, color)
			transaction = [
				[[self._set_objs_styles, initial_styles]],
				[[self._stroke_objs, objs, color]],
				False]
			self.add_undo(transaction)

	def _apply_trafo(self, objs, trafo):
		before = []
		after = []
		for obj in objs:
			before.append(obj.get_trafo_snapshot())
			obj.apply_trafo(trafo)
			after.append(obj.get_trafo_snapshot())
		self.selection.update_bbox()
		return (before, after)

	def _set_snapshots(self, snapshots):
		for snapshot in snapshots:
			obj = snapshot[0]
			obj.set_trafo_snapshot(snapshot)
		self.selection.update_bbox()

	def transform_selected(self, trafo, copy=False):
		if self.selection.objs:
			objs = [] + self.selection.objs
			if copy:
				copied_objs = []
				for obj in objs:
					copied_obj = obj.copy()
					copied_obj.update()
					copied_objs.append(copied_obj)
				self._apply_trafo(copied_objs, trafo)
				before = self._get_layers_snapshot()
				self.methods.append_objects(copied_objs,
										self.presenter.active_layer)
				after = self._get_layers_snapshot()
				transaction = [
					[[self._set_layers_snapshot, before]],
					[[self._set_layers_snapshot, after]],
					False]
				self.add_undo(transaction)
				self.selection.set(copied_objs)
			else:
				before, after = self._apply_trafo(objs, trafo)
				transaction = [
					[[self._set_snapshots, before]],
					[[self._set_snapshots, after]],
					False]
				self.add_undo(transaction)

