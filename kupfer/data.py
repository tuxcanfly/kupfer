import gtk
import gobject
import itertools
from . import kupfer
import threading

class SearchThread(threading.Thread):
	def __init__(self, sender, coll, key, signal, **kwargs):
		super(SearchThread, self).__init__(**kwargs)
		self.sender = sender
		self.rankables = coll
		self.key = key or ""
		self.signal = signal

	def run(self):
		sobj = kupfer.Search(self.rankables)
		matches = sobj.search_objects(self.key)
		if len(matches):
			match = matches[0]
		else:
			match = None
		gobject.idle_add(self.sender.emit, self.signal, self.key, match, iter(matches))

class DataController (gobject.GObject):
	"""
	Sources <-> Actions controller
	"""
	__gtype_name__ = "DataController"
	def __init__(self, datasource):
		super(DataController, self).__init__()
		self.source_rebase(datasource)

	def do_search(self, source, key):
		rankables = ((leaf.value, leaf) for leaf in source.get_leaves())
		st = SearchThread(self, rankables, key, "search-result")
		st.start()

	def search(self, key):
		gobject.idle_add(self.do_search, self.source, key)

	def do_predicate_search(self, rankable, key=None):
		if rankable:
			leaves = rankable.get_actions()
		else:
			leaves = []
		if not key:
			matches = [kupfer.Rankable(leaf.name, leaf) for leaf in leaves]
			try:
				match = matches[0]
			except IndexError: match = None
			self.emit("predicate-result", key, match, iter(matches))
		else:
			leaves = [(leaf.name, leaf) for leaf in leaves]
			st = SearchThread(self, leaves, key, "predicate-result")
			st.start()

	def search_predicate(self, item, key=None):
		self.do_predicate_search(item, key)

	def source_rebase(self, src):
		self.source_stack = []
		self.source = src
		self.refresh_data()
	
	def push_source(self, src):
		self.source_stack.append(self.source)
		self.source = src
	
	def pop_source(self):
		if not len(self.source_stack):
			raise Exception
		else:
			self.source = self.source_stack.pop()
	
	def refresh_data(self):
		pass
	
	def refresh_actions(self, leaf):
		"""
		Updates the Actions widget, given a selected leaf object

		leaf can be none
		"""
		if not leaf:
			sobj = None
		else:
			actions = leaf.get_actions()
			sobj = kupfer.Search(((str(act), act) for act in actions))
		self.action_search.set_search_object(sobj)

	def _cursor_changed(self, widget, leaf):
		"""
		Selected item changed in Leaves widget
		"""
		self.refresh_actions(leaf)
	
	def _browse_up(self, controller, leaf):
		try:
			self.pop_source()
		except:
			if self.source.has_parent():
				self.source_rebase(self.source.get_parent())
		self.refresh_data()
	
	def _browse_down(self, controller, leaf):
		if not leaf.has_content():
			return
		self.push_source(leaf.content_source())
		self.refresh_data()

	def _search_cancelled(self, widget, state):
		try:
			while True:
				self.pop_source()
		except:
			self.refresh_data()

	def _activate(self, controller, leaf, action):
		self.eval_action(action, leaf)
	
	def eval_action(self, action, leaf):
		"""
		Evaluate an action with the given leaf
		"""
		if not action or not leaf:
			print "No action", (action, leaf)
			return
		new_source = action.activate(leaf)
		# handle actions returning "new contexts"
		if action.is_factory() and new_source:
			self.push_source(new_source)
			self.refresh_data()
		else:
			self.emit("launched-action", leaf, action)

gobject.type_register(DataController)
gobject.signal_new("search-result", DataController, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_STRING, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT ))
gobject.signal_new("predicate-result", DataController, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_STRING, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT ))
gobject.signal_new("new-source", DataController, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT, gobject.TYPE_BOOLEAN))
gobject.signal_new("launched-action", DataController, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT))
