from indra.tools import assemble_corpus as ac
from indra.sources.eidos import migration_table_processor as mtp


if __name__ == '__main__':
    fname = 'Initial annotation exercise for migration use case.xlsx'
    stmts = mtp.process_workbook(fname)
