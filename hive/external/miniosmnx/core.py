from itertools import groupby

import networkx as nx
import numpy as np
import pandas as pd

from .geo_utils import get_largest_component
from .geo_utils import great_circle_vec
from .geo_utils import overpass_json_from_file

# useful osm tags - note that load_graphml expects a consistent set of tag names
# for parsing
USEFUL_TAGS_NODE = ['ref', 'highway']
USEFUL_TAGS_PATH = ['bridge', 'tunnel', 'oneway', 'lanes', 'ref', 'name',
                    'highway', 'maxspeed', 'service', 'access', 'area',
                    'landuse', 'width', 'est_width', 'junction']
# all one-way mode to maintain original OSM node order
# when constructing graphs specifically to save to .osm xml file
ALL_ONEWAY = True

# default CRS to set when creating graphs
DEFAULT_CRS = '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs'


def get_node(element):
    """
    Convert an OSM node element into the format for a networkx node.

    Parameters
    ----------
    element : dict
        an OSM node element

    Returns
    -------
    dict
    """

    node = {}
    node['y'] = element['lat']
    node['x'] = element['lon']
    node['osmid'] = element['id']
    if 'tags' in element:
        for useful_tag in USEFUL_TAGS_NODE:
            if useful_tag in element['tags']:
                node[useful_tag] = element['tags'][useful_tag]
    return node


def get_path(element):
    """
    Convert an OSM way element into the format for a networkx graph path.

    Parameters
    ----------
    element : dict
        an OSM way element

    Returns
    -------
    dict
    """

    path = {}
    path['osmid'] = element['id']

    # remove any consecutive duplicate elements in the list of nodes
    grouped_list = groupby(element['nodes'])
    path['nodes'] = [group[0] for group in grouped_list]

    if 'tags' in element:
        for useful_tag in USEFUL_TAGS_PATH:
            if useful_tag in element['tags']:
                path[useful_tag] = element['tags'][useful_tag]
    return path


def parse_osm_nodes_paths(osm_data):
    """
    Construct dicts of nodes and paths with key=osmid and value=dict of
    attributes.

    Parameters
    ----------
    osm_data : dict
        JSON response from from the Overpass API

    Returns
    -------
    nodes, paths : tuple
    """

    nodes = {}
    paths = {}
    for element in osm_data['elements']:
        if element['type'] == 'node':
            key = element['id']
            nodes[key] = get_node(element)
        elif element['type'] == 'way':  # osm calls network paths 'ways'
            key = element['id']
            paths[key] = get_path(element)

    return nodes, paths


def remove_isolated_nodes(G):
    """
    Remove from a graph all the nodes that have no incident edges (ie, node
    degree = 0).

    Parameters
    ----------
    G : networkx multidigraph
        the graph from which to remove nodes

    Returns
    -------
    networkx multidigraph
    """

    isolated_nodes = [node for node, degree in dict(G.degree()).items() if degree < 1]
    G.remove_nodes_from(isolated_nodes)
    return G


def add_edge_lengths(G):
    """
    Add length (meters) attribute to each edge by great circle distance between
    nodes u and v.

    Parameters
    ----------
    G : networkx multidigraph

    Returns
    -------
    G : networkx multidigraph
    """

    # first load all the edges' origin and destination coordinates as a
    # dataframe indexed by u, v, key
    coords = np.array([[u, v, k, G.nodes[u]['y'], G.nodes[u]['x'], G.nodes[v]['y'], G.nodes[v]['x']] for u, v, k in
                       G.edges(keys=True)])
    df_coords = pd.DataFrame(coords, columns=['u', 'v', 'k', 'u_y', 'u_x', 'v_y', 'v_x'])
    df_coords[['u', 'v', 'k']] = df_coords[['u', 'v', 'k']].astype(np.int64)
    df_coords = df_coords.set_index(['u', 'v', 'k'])

    # then calculate the great circle distance with the vectorized function
    gc_distances = great_circle_vec(lat1=df_coords['u_y'],
                                    lng1=df_coords['u_x'],
                                    lat2=df_coords['v_y'],
                                    lng2=df_coords['v_x'])

    # fill nulls with zeros and round to the millimeter
    gc_distances = gc_distances.fillna(value=0).round(3)
    nx.set_edge_attributes(G, name='length', values=gc_distances.to_dict())

    return G


def add_path(G, data, one_way):
    """
    Add a path to the graph.

    Parameters
    ----------
    G : networkx multidigraph
    data : dict
        the attributes of the path
    one_way : bool
        if this path is one-way or if it is bi-directional

    Returns
    -------
    None
    """

    # extract the ordered list of nodes from this path element, then delete it
    # so we don't add it as an attribute to the edge later
    path_nodes = data['nodes']
    del data['nodes']

    # set the oneway attribute to the passed-in value, to make it consistent
    # True/False values, but only do this if you aren't forcing all edges to
    # oneway with the ALL_ONEWAY setting. With the ALL_ONEWAY setting, you
    # likely still want to preserve the original OSM oneway attribute.
    if not ALL_ONEWAY:
        data['oneway'] = one_way

    # zip together the path nodes so you get tuples like (0,1), (1,2), (2,3)
    # and so on
    path_edges = list(zip(path_nodes[:-1], path_nodes[1:]))
    G.add_edges_from(path_edges, **data)

    # if the path is NOT one-way
    if not one_way:
        # reverse the direction of each edge and add this path going the
        # opposite direction
        path_edges_opposite_direction = [(v, u) for u, v in path_edges]
        G.add_edges_from(path_edges_opposite_direction, **data)


def add_paths(G, paths, bidirectional=False):
    """
    Add a collection of paths to the graph.

    Parameters
    ----------
    G : networkx multidigraph
    paths : dict
        the paths from OSM
    bidirectional : bool
        if True, create bidirectional edges for one-way streets


    Returns
    -------
    None
    """

    # the list of values OSM uses in its 'oneway' tag to denote True
    # updated list of of values OSM uses based on https://www.geofabrik.de/de/data/geofabrik-osm-gis-standard-0.7.pdf 
    osm_oneway_values = ['yes', 'true', '1', '-1', 'T', 'F']

    for data in paths.values():

        if ALL_ONEWAY is True:
            add_path(G, data, one_way=True)
        # if this path is tagged as one-way and if it is not a walking network,
        # then we'll add the path in one direction only
        elif ('oneway' in data and data['oneway'] in osm_oneway_values) and not bidirectional:
            if data['oneway'] == '-1' or data['oneway'] == 'T':
                # paths with a one-way value of -1 or T are one-way, but in the
                # reverse direction of the nodes' order, see osm documentation 
                data['nodes'] = list(reversed(data['nodes']))
            # add this path (in only one direction) to the graph
            add_path(G, data, one_way=True)

        elif ('junction' in data and data['junction'] == 'roundabout') and not bidirectional:
            # roundabout are also oneway but not tagged as is
            add_path(G, data, one_way=True)

        # else, this path is not tagged as one-way or it is a walking network
        # (you can walk both directions on a one-way street)
        else:
            # add this path (in both directions) to the graph and set its
            # 'oneway' attribute to False. if this is a walking network, this
            # may very well be a one-way street (as cars/bikes go), but in a
            # walking-only network it is a bi-directional edge
            add_path(G, data, one_way=False)

    return G


def create_graph(response_jsons, name='unnamed', retain_all=False, bidirectional=False):
    """
    Create a networkx graph from Overpass API HTTP response objects.

    Parameters
    ----------
    response_jsons : list
        list of dicts of JSON responses from from the Overpass API
    name : string
        the name of the graph
    retain_all : bool
        if True, return the entire graph even if it is not connected
    bidirectional : bool
        if True, create bidirectional edges for one-way streets

    Returns
    -------
    networkx multidigraph
    """

    # make sure we got data back from the server requests
    elements = []
    for response_json in response_jsons:
        elements.extend(response_json['elements'])
    if len(elements) < 1:
        raise Exception('There are no data elements in the response JSON objects')

    # create the graph as a MultiDiGraph and set the original CRS to DEFAULT_CRS
    G = nx.MultiDiGraph(name=name, crs=DEFAULT_CRS)

    # extract nodes and paths from the downloaded osm data
    nodes = {}
    paths = {}
    for osm_data in response_jsons:
        nodes_temp, paths_temp = parse_osm_nodes_paths(osm_data)
        for key, value in nodes_temp.items():
            nodes[key] = value
        for key, value in paths_temp.items():
            paths[key] = value

    # add each osm node to the graph
    for node, data in nodes.items():
        G.add_node(node, **data)

    # add each osm way (aka, path) to the graph
    G = add_paths(G, paths, bidirectional=bidirectional)

    # retain only the largest connected component, if caller did not
    # set retain_all=True
    if not retain_all:
        G = get_largest_component(G)

    # add length (great circle distance between nodes) attribute to each edge to
    # use as weight
    if len(G.edges) > 0:
        G = add_edge_lengths(G)

    return G


def graph_from_file(filename, bidirectional=False,
                    retain_all=False, name='unnamed'):
    """
    Create a networkx graph from OSM data in an XML file.

    Parameters
    ----------
    filename : string
        the name of a file containing OSM XML data
    bidirectional : bool
        if True, create bidirectional edges for one-way streets
    simplify : bool
        if True, simplify the graph topology
    retain_all : bool
        if True, return the entire graph even if it is not connected
    name : string
        the name of the graph

    Returns
    -------
    networkx multidigraph
    """
    # transmogrify file of OSM XML data into JSON
    response_jsons = [overpass_json_from_file(filename)]

    # create graph using this response JSON
    G = create_graph(response_jsons, bidirectional=bidirectional,
                     retain_all=retain_all, name=name)

    return G
