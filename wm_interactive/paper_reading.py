from ipywidgets import widgets
import xml.etree.ElementTree as ET
from IPython.display import display, Markdown, Javascript

from indra.sources import eidos
from indra.assemblers.cag import CAGAssembler
from indra.literature import elsevier_client

def printmd(string):
    display(Markdown(string))

def on_search(b):
    global titles
    global articles
    global search_term
    piis = elsevier_client.get_piis(search_term.value, start_year=2017)
    print('We found a total of %d papers%s.' % (len(piis), (', I\'ll show you the first 10' if len(piis) > 10 else '')))
    articles = [elsevier_client.download_article(pii, id_type='pii') for pii in piis[:10]]
    titles = [ET.fromstring(content).findall('*/dc:title',
              namespaces=elsevier_client.elsevier_ns)[0].text.strip() for content in articles]
    for idx, title in enumerate(titles):
        clean_pii = piis[idx].replace('(', '').replace(')', '')
        printmd('* %d: <a href="https://www.sciencedirect.com/science/article/pii/%s" target="_blank">%s</a>' % (idx, clean_pii, title))
        
def on_read(b):
    global articles
    global statements
    raw_txt = elsevier_client.extract_text(articles[int(paper_id.value)])
    if 'Internal Server Error' in raw_txt:
        print('Sorry, that paper was not accessible for reading.')
        statements = []
    ep = eidos.process_text(raw_txt, webservice='http://localhost:5000')
    statements = ep.statements
    print('We extracted %d statements:' % len(statements))
    for stmt in statements:
        sg = stmt.subj.db_refs['UN'][0][0].split('/')[-1]
        og = stmt.obj.db_refs['UN'][0][0].split('/')[-1]
        printmd('* **%s**(%s) %s **%s**(%s)' % (sg, stmt.subj.name, '->' if stmt.overall_polarity() == 1 else '-|', og, stmt.obj.name))

def standardize_names(stmts):
    for stmt in stmts:
        stmt.subj.name = stmt.subj.db_refs['UN'][0][0].split('/')[-1].capitalize().replace('_', ' ')
        stmt.obj.name = stmt.obj.db_refs['UN'][0][0].split('/')[-1].capitalize().replace('_', ' ')
    return stmts
