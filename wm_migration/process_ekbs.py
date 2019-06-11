import glob
from indra.sources import cwms

if __name__ == '__main__':
    fnames = glob.glob('ekbs/*.ekb')
    #fnames = ['ekbs/t_South-Sudan_20190611T102227_r.ekb']
    stmts = []
    for fname in fnames:
        print('Reading %s' % fname)
        cp = cwms.process_ekb_file(fname)
        print('Got %d statements' % len(cp.statements))
        stmts += cp.statements
