import os
import json
import kappy
import numpy
import pkgutil
import networkx
import subprocess
import matplotlib.pyplot as plt
from IPython.display import IFrame
from pysb.export import export
from indra.assemblers.english import EnglishAssembler
from indra.explanation.reporting import stmts_from_pysb_path
from indra.util.kappa_util import im_json_to_graph

def list_submodules(module):
    names = sorted([pkg.name for pkg in
                    pkgutil.iter_modules(module.__path__)])
    for name in names:
        print(name)


def plot_sim_result(model, res, **kwargs):
    xsize = kwargs.get('xsize', 14)
    ysize = kwargs.get('ysize', 6)
    plt.figure(figsize=(xsize, ysize))
    for idx, cp in enumerate(model.species):
        plt.plot(res.tout[0], res.all['__s%d' % idx],
                 label=str(cp))
    plt.xlabel('Time')
    plt.ylabel('Number of molecules')
    plt.legend(loc='right')
    plt.show()


def draw_reaction_network(pysb_model):
    """Generate a PySB/BNG reaction network as a PNG file."""
    for m in pysb_model.monomers:
        pysb_assembler.set_extended_initial_condition(pysb_model, m, 0)
    fname = 'model_rxn'
    diagram_dot = render_reactions.run(pysb_model)
    # TODO: use specific PySB/BNG exceptions and handle them
    # here to show meaningful error messages
    with open(fname + '.dot', 'wt') as fh:
        fh.write(diagram_dot)
    subprocess.call(('dot -T png -o %s.png %s.dot' %
                     (fname, fname)).split(' '))
    abs_path = os.path.abspath(os.getcwd())
    full_path = os.path.join(abs_path, fname + '.png')
    return full_path

def draw_influence_map(pysb_model):
    """Generate a Kappa influence map, draw it and save it as a PNG."""
    im = make_influence_map(pysb_model)
    fname = 'model_im'
    abs_path = os.path.abspath(os.getcwd())
    full_path = os.path.join(abs_path, fname + '.png')
    im_agraph = networkx.nx_agraph.to_agraph(im)
    im_agraph.draw(full_path, prog='dot')
    return full_path


def make_influence_map(pysb_model):
    """Return a Kappa influence map."""
    kappa = kappy.KappaStd()
    model_str = export(pysb_model, 'kappa')
    kappa.add_model_string(model_str)
    kappa.project_parse()
    imap = kappa.analyses_influence_map()
    im = im_json_to_graph(imap)
    for param in pysb_model.parameters:
        try:
            im.remove_node(param.name)
        except:
            pass
    return im

def path_to_english(path, model, stmts):
    path_stmts = stmts_from_pysb_path(path, model, stmts)
    ea = EnglishAssembler(path_stmts)
    return ea.make_model()

def find_multiev_stmt(stmts):
    for stmt in stmts:
        sources = set([e.source_api for e in stmt.evidence])
        if len(sources) >= 3:
            return stmt
