import os
import xml.sax

import networkx as nx
import numpy as np


def great_circle_vec(lat1, lng1, lat2, lng2, earth_radius=6371009):
    """
    Vectorized function to calculate the great-circle distance between two
    points or between vectors of points, using haversine.

    Parameters
    ----------
    lat1 : float or array of float
    lng1 : float or array of float
    lat2 : float or array of float
    lng2 : float or array of float
    earth_radius : numeric
        radius of earth in units in which distance will be returned (default is
        meters)

    Returns
    -------
    distance : float or vector of floats
        distance or vector of distances from (lat1, lng1) to (lat2, lng2) in
        units of earth_radius
    """

    phi1 = np.deg2rad(lat1)
    phi2 = np.deg2rad(lat2)
    d_phi = phi2 - phi1

    theta1 = np.deg2rad(lng1)
    theta2 = np.deg2rad(lng2)
    d_theta = theta2 - theta1

    h = np.sin(d_phi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(d_theta / 2) ** 2
    h = np.minimum(1.0, h)  # protect against floating point errors

    arc = 2 * np.arcsin(np.sqrt(h))

    # return distance in units of earth_radius
    distance = arc * earth_radius
    return distance


class OSMContentHandler(xml.sax.handler.ContentHandler):
    """
    SAX content handler for OSM XML.

    Used to build an Overpass-like response JSON object in self.object. For format
    notes, see http://wiki.openstreetmap.org/wiki/OSM_XML#OSM_XML_file_format_notes
    and http://overpass-api.de/output_formats.html#json
    """

    def __init__(self):
        self._element = None
        self.object = {'elements': []}

    def startElement(self, name, attrs):
        if name == 'osm':
            self.object.update({k: attrs[k] for k in attrs.keys()
                                if k in ('version', 'generator')})

        elif name in ('node', 'way'):
            self._element = dict(type=name, tags={}, nodes=[], **attrs)
            self._element.update({k: float(attrs[k]) for k in attrs.keys()
                                  if k in ('lat', 'lon')})
            self._element.update({k: int(attrs[k]) for k in attrs.keys()
                                  if k in ('id', 'uid', 'version', 'changeset')})

        elif name == 'tag':
            self._element['tags'].update({attrs['k']: attrs['v']})

        elif name == 'nd':
            self._element['nodes'].append(int(attrs['ref']))

        elif name == 'relation':
            # Placeholder for future relation support.
            # Look for nested members and tags.
            pass

    def endElement(self, name):
        if name in ('node', 'way'):
            self.object['elements'].append(self._element)


def induce_subgraph(G, node_subset):
    """
    Induce a subgraph of G.

    Parameters
    ----------
    G : networkx multidigraph
    node_subset : list-like
        the subset of nodes to induce a subgraph of G

    Returns
    -------
    G2 : networkx multidigraph
        the subgraph of G induced by node_subset
    """

    node_subset = set(node_subset)

    # copy nodes into new graph
    G2 = G.__class__()
    G2.add_nodes_from((n, G.nodes[n]) for n in node_subset)

    # copy edges to new graph, including parallel edges
    if G2.is_multigraph:
        G2.add_edges_from((n, nbr, key, d)
                          for n, nbrs in G.adj.items() if n in node_subset
                          for nbr, keydict in nbrs.items() if nbr in node_subset
                          for key, d in keydict.items())
    else:
        G2.add_edges_from((n, nbr, d)
                          for n, nbrs in G.adj.items() if n in node_subset
                          for nbr, d in nbrs.items() if nbr in node_subset)

    # update graph attribute dict, and return graph
    G2.graph.update(G.graph)
    return G2


def get_largest_component(G, strongly=False):
    """
    Return a subgraph of the largest weakly or strongly connected component
    from a directed graph.

    Parameters
    ----------
    G : networkx multidigraph
    strongly : bool
        if True, return the largest strongly instead of weakly connected
        component

    Returns
    -------
    G : networkx multidigraph
        the largest connected component subgraph from the original graph
    """

    if strongly:
        # if the graph is not connected retain only the largest strongly connected component
        if not nx.is_strongly_connected(G):
            # get all the strongly connected components in graph then identify the largest
            sccs = nx.strongly_connected_components(G)
            largest_scc = max(sccs, key=len)
            G = induce_subgraph(G, largest_scc)


    else:
        # if the graph is not connected retain only the largest weakly connected component
        if not nx.is_weakly_connected(G):
            # get all the weakly connected components in graph then identify the largest
            wccs = nx.weakly_connected_components(G)
            largest_wcc = max(wccs, key=len)
            G = induce_subgraph(G, largest_wcc)

    return G


def overpass_json_from_file(filename):
    """
    Read OSM XML from input_config filename and return Overpass-like JSON.

    Parameters
    ----------
    filename : string
        name of file containing OSM XML data

    Returns
    -------
    OSMContentHandler object
    """

    _, ext = os.path.splitext(filename)

    if ext != '.xml':
        raise NotImplementedError('only .xml files are supported')
    else:
        opener = lambda fn: open(fn, mode='rb')

    with opener(filename) as file:
        handler = OSMContentHandler()
        xml.sax.parse(file, handler)
        return handler.object
