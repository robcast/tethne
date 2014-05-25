import tethne.networks as nt
from tethne.classes import GraphCollection


class GraphCollectionManager(object):
    """
    Base class for GraphCollection managers.
    """

    def __init__(self, D):
        """
        
        Parameters
        ----------
        D : :class:`.DataCollection`
        """

        self.D = D

class PaperGraphCollectionManager(GraphCollectionManager):
    """
    Builds a :class:`.GraphCollection` with method in 
    :mod:`tethne.networks.papers` from a :class:`.DataCollection` .
    """

    def build(self, graph_axis, graph_type, **kwargs):
        """
        Generates graphs for each slice along graph_axis in
        :class:`.DataCollection` D.
        
        Other axes in D are treated as attributes.
        
        **Usage**
    
        .. code-block:: python

           >>> import tethne.readers as rd
           >>> data = rd.wos.read("/Path/to/wos/data.txt")
           >>> from tethne.data import DataCollection
           >>> D = DataCollection(data) # Indexed by wosid, by default.
           >>> D.slice('date', 'time_window', window_size=4)
           >>> from tethne.builders import paperCollectionBuilder
           >>> builder = paperCollectionBuilder(D)
           >>> C = builder.build('date', 'bibliographic_coupling', threshold=2)
           >>> C
           <tethne.data.GraphCollection at 0x104ed3550>
           
           """
        
        # TODO: Check to make sure we have the right stuff.
        
        C = GraphCollection()
        
        # Build a Graph for each slice.
        for key, pids in self.D.axes[graph_axis].iteritems():
            data = [ self.D.data[p] for p in pids ]
            kwargs['node_attribs'] = self.D.get_axes()
            kwargs['node_id'] = self.D.index_by
            C[key] = nt.papers.__dict__[graph_type](data, **kwargs)

        return C
        
class TopicGraphCollectionManager(GraphCollectionManager):
    """
    Builds a :class:`.GraphCollection` with method in
    :mod:`tethne.networks.topics` from a :class:`.DataCollection` .
    """
    
    def build(self, graph_axis, graph_type, **kwargs):
        """
        Generates a graph for each slice along graph_axis in
        :class:`.DataCollection` D.
        
        Other axes in D are treated as attributes.
        """
        
        if self.D.model is None:
            raise RuntimeError('No corpus model in this DataCollection')
        
        C = GraphCollection()
        
        for key in sorted(self.D.axes[graph_axis].keys()):
            pids = self.D.axes[graph_axis][key]
            data = [ self.D.data[p] for p in pids ]
            papers = [ self.D.model.lookup[p] for p in pids ]
            C[key] = nt.topics.__dict__[graph_type](self.D.model, papers=papers, **kwargs)
            print key, len(papers), len(C[key].edges())
        
        return C

class AuthorGraphCollectionManager(GraphCollectionManager):
    """
    Builds a :class:`.GraphCollection` with method in 
    :mod:`tethne.networks.authors` from a :class:`.DataCollection` .
    """
    
    def build(self, graph_axis, graph_type, **kwargs):
        """
        Generates graphs for each slice along graph_axis in
        :class:`.DataCollection` D.
        
        Other axes in D are treated as attributes.
        
        **Usage**
    
        .. code-block:: python

           >>> import tethne.readers as rd
           >>> data = rd.wos.read("/Path/to/wos/data.txt")
           >>> from tethne.data import DataCollection
           >>> D = DataCollection(data) # Indexed by wosid, by default.
           >>> D.slice('date', 'time_window', window_size=4)
           >>> from tethne.builders import authorCollectionBuilder
           >>> builder = authorCollectionBuilder(D)
           >>> C = builder.build('date', 'coauthors')
           >>> C
           <tethne.data.GraphCollection at 0x104ed3550>
           
           """
        
        # TODO: Check to make sure we have the right stuff.
        
        C = GraphCollection()
        
        # Build a Graph for each slice.
        for key, pids in self.D.axes[graph_axis].iteritems():
            data = [ self.D.data[p] for p in pids ]
            C[key] = nt.authors.__dict__[graph_type](data, **kwargs)

        return C