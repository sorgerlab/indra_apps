import os
from indra.literature import elsevier_client
from indra.sources.eidos import eidos_cli

if __name__ == '__main__':
    # Search for all the relevant literature
    searches = ['food insecurity intervention', 'food security intervention']
    all_piis = []
    for search_term in searches:
        fname = search_term.replace(' ', '_') + '.txt'
        if not os.path.exists(fname):
            print('Getting PIIs for %s' % search_term)
            piis = elsevier_client.get_piis(search_term)
            with open(fname, 'w') as fh:
                for pii in piis:
                    fh.write('%s\n' % pii)
        else:
            print('Loading PIIs for %s' % search_term)
            with open(fname, 'r') as fh:
                piis = [l.strip() for l in fh.readlines()]
        all_piis += piis
    all_piis = list(set(all_piis))
    print('Got %d PIIs' % len(all_piis))

    # Download all the XML content
    for pii in all_piis:
        fname = 'xml/%s.xml' % pii.replace('/', '_')
        if not os.path.exists(fname):
            print('Donwloading %s' % pii)
            res = elsevier_client.download_article(pii, 'pii')
            with open(fname, 'wb') as fh:
                fh.write(res.encode('utf-8'))
        else:
            print('Cached %s' % pii)


    # Strip out the text from all the XML content
    for pii in all_piis:
        fname = 'xml/%s.xml' % pii.replace('/', '_')
        with open(fname, 'rb') as fh:
            xml_content = fh.read().decode('utf-8')
        txt = elsevier_client.extract_text(xml_content)
        if not txt:
            continue
        txt_fname = 'txt/%s.txt' % pii.replace('/', '_')
        with open(txt_fname, 'wb') as fh:
            fh.write(txt.encode('utf-8'))


    # Now run Eidos on the documents
    in_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'txt')
    out_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'jsonld')
    eidos_cli.extract_from_directory(in_folder, out_folder)
