import os
import numpy as np
import logging
from Bio import SeqIO
from collections import Counter, defaultdict
from .bc_aligner import CustomBCAligner
from .bc_decoders import BCDecoder, SBCDecoder
from .misc import gzip_friendly_open

log = logging.getLogger(__name__)


commonseq1_options = ['GTCAGTACGTACGAGTC'[i:] for i in range(4)]
commonseq2_RNA = 'GTACTCGCAGTAGTCGACACGTC'
commonseq2_gDNA = 'GTACTCGCAGTAGTC'

def process_RNA_fastqs(arguments):
    """
    Output single file with parsed bcs from bc_fastq in read names and seqs from paired_fastq.
    """
    paired_fpath = arguments.paired_fastq_file
    paired_bname = os.path.splitext(paired_fpath[:-3] if paired_fpath.endswith('.gz') else paired_fpath)[0]
    out_fname = f'{os.basename(paired_bname)}.fq'
    out_fpath = os.path.join(arguments.out_dir, out_fname)

    log.info('Processing fastqs:')
    log.info(f'  barcode fastq: {arguments.bc_fastq_file}')
    log.info(f'  paired fastq:  {arguments.paired_fastq_file}')
    log.info('Writing output to:')
    log.info(f'  {out_fpath}')

    aligners = [CustomBCAligner('N'*9, cso, 'N'*9, commonseq2_RNA, 'N'*8, 'N'*8) for cso in commonseq1_options]
    def parse_recs(bc_rec, p_rec):
        bc_seq = str(bc_rec.seq)
        score, pieces = max([al.find_norm_score_and_pieces(bc_seq) for al in aligners])
        pieces_str = ','.join(pieces)
        name = f'{pieces_str}/{score}/{bc_rec.id}'
        bc_rec.id = name
        bc_rec.name = name
        bc_rec.description = ''
        return score, rec

    with gzip_friendly_open(arguments.bc_fastq_file) as bcfqh, \
            gzip_friendly_open(arguments.paired_fastq_file) as pfqh, \
            open(out_fpath, 'w') as out:
        first_scores_and_recs = []
        for i, (bc_rec, p_rec) in enumerate(zip(SeqIO.parse(bcfqh, 'fastq'), SeqIO.parse(pfqh, 'fastq'))):
            first_scores_and_recs.append(parse_recs(bc_rec, p_rec))
            if i >= 100000:
                break

        scores = [score for score, rec in first_scores_and_recs]
        thresh = np.average(scores) - 2 * np.std(scores)
        log.info(f'Score threshold: {thresh:.2f}')
        out_recs = [rec for score, rec in first_scores_and_recs if score >= thresh]
        SeqIO.write(out_recs, out, 'fastq')

        for bc_rec, p_rec in zip(SeqIO.parse(bcfqh, 'fastq'), SeqIO.parse(pfqh, 'fastq')):
            score, rec = parse_recs(bc_rec, p_rec)
            if score >= thresh:
                SeqIO.write(rec, out, 'fastq')





def process_gDNA_fastq(arguments):
    aligners = [CustomBCAligner('N'*9, cso, 'N'*9, commonseq2_gDNA) for cso in commonseq1_options]
    with open(out_fpath, 'w') as out:
        for rec in SeqIO.parse(gzip_friendly_open(bc_fastq_fpath), 'fastq'):
            seq = str(rec.seq)
            norm_score, pieces, end_pos = max([al.find_norm_score_pieces_and_end_pos(seq) for al in aligners])
            pieces_str = ','.join(pieces)
            name = f'{pieces_str}/{norm_score}/{rec.id}'
            rec = rec[end_pos:]
            rec.id = name
            rec.name = name
            rec.description = ''
            SeqIO.write(rec, out, 'fastq')


def norm_score_from_rec(rec):
    return float(str(rec.id).split('/')[1])


def bc_and_sbc_counter_from_fastq(bc_fastq_fpath, bc_parser):
    # Determine minimum norm_score threshold = mean-2sigma. See notebook for figures
    norm_scores_sample = []
    for i, rec in enumerate(SeqIO.parse(open(bc_fastq_fpath), 'fastq')):
        if i >= 100000:
            break
        norm_scores_sample.append(norm_score_from_rec(rec))
    thresh = np.average(norm_scores_sample) - 2 * np.std(norm_scores_sample)





def process_gDNA_fastqs(arguments):
    aligners = [CustomBCAligner('N'*9, cso, 'N'*9, commonseq2_gDNA) for cso in commonseq1_options]
    with open(out_fpath, 'w') as out:
        for rec in SeqIO.parse(gzip_friendly_open(bc_fastq_fpath), 'fastq'):
            seq = str(rec.seq)
            norm_score, pieces, end_pos = max([al.find_norm_score_pieces_and_end_pos(seq) for al in aligners])
            pieces_str = ','.join(pieces)
            name = f'{pieces_str}/{norm_score}/{rec.id}'
            rec = rec[end_pos:]
            rec.id = name
            rec.name = name
            rec.description = ''
            SeqIO.write(rec, out, 'fastq')


def norm_score_from_rec(rec):
    return float(str(rec.id).split('/')[1])


def bc_and_sbc_counter_from_fastq(bc_fastq_fpath, bc_parser):
    # Determine minimum norm_score threshold = mean-2sigma. See notebook for figures
    norm_scores_sample = []
    for i, rec in enumerate(SeqIO.parse(open(bc_fastq_fpath), 'fastq')):
        if i >= 100000:
            break
        norm_scores_sample.append(norm_score_from_rec(rec))
    thresh = np.average(norm_scores_sample) - 2 * np.std(norm_scores_sample)
    print(f'Norm score threshold: {thresh:.2f} for {bc_fastq_fpath}')

    bc_sbc_cntr = defaultdict(Counter)
    for rec in SeqIO.parse(open(bc_fastq_fpath), 'fastq'):
        norm_score = norm_score_from_rec(rec)
        if norm_score < thresh:
            continue
        bcs, sbc = bc_parser.bc_and_sbc_from_rec(rec)
        if None not in bcs and sbc is not None:
            bc_sbc_cntr[bcs][sbc] += 1
    return bc_sbc_cntr


