#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
work="$(mktemp -d)"
trap 'command rm -rf "$work"' EXIT
cd "$work"
mkdir fgbio fgumi

python3 "$repo/scripts/fixtures/simulate_umis.py" in
ref=in/ref.fasta
samtools faidx "$ref"
samtools dict -o in/ref.dict "$ref"
bwa index "$ref" 2> /dev/null

samtools view -b -o in/unmapped.bam in/unmapped.sam
samtools view -b -o in/umi_in_name.bam in/umi_in_name.sam
samtools sort -o in/mapped.bam in/mapped.sam
samtools index in/mapped.bam
fgbio SortBam -i in/mapped.bam -o in/mapped.qn.bam -s Queryname

# Consensus reads are unmapped, so they are aligned and zipped back to their tags to review.
align() {
  samtools fastq -n "$1" 2> /dev/null | bwa mem -p -K 100000000 -t 2 "$ref" - 2> /dev/null > "$1.aligned.sam"
  fgbio ZipperBams -u "$1" -i "$1.aligned.sam" -r "$ref" -o "$2" -s Coordinate
  samtools index "$2"
}

fgbio CorrectUmis -i in/unmapped.bam -o in/fgbio.corrected.bam -r in/fgbio.rejected.bam \
  -M fgbio/correct_umis.metrics.txt -U in/umis.txt -m 1 -d 2
fgbio GroupReadsByUmi -i in/mapped.bam -o in/fgbio.grouped.bam -s Paired -e 1 \
  -f fgbio/group.family_sizes.txt -g fgbio/group.grouping_metrics.txt
fgbio GroupReadsByUmi -i in/mapped.bam -o in/fgbio.grouped.adjacency.bam -s Adjacency -e 1
fgbio CollectDuplexSeqMetrics -i in/fgbio.grouped.bam -o fgbio/duplex -u true
fgbio CallDuplexConsensusReads -i in/fgbio.grouped.bam -o in/fgbio.duplex.bam -M 1 \
  -s fgbio/duplex.consensus_stats.txt
fgbio CallMolecularConsensusReads -i in/fgbio.grouped.adjacency.bam -o in/fgbio.simplex.bam -M 1 \
  -s fgbio/simplex.consensus_stats.txt
fgbio ClipBam -i in/mapped.qn.bam -o in/fgbio.clipped.bam -r "$ref" -m fgbio/clip.metrics.txt \
  --clip-overlapping-reads true --clip-bases-past-mate true --read-one-five-prime 2
fgbio ErrorRateByReadPosition -i in/mapped.bam -r "$ref" -o fgbio/collapsed
fgbio ErrorRateByReadPosition -i in/mapped.bam -r "$ref" -o fgbio/uncollapsed --collapse false
fgbio CallOverlappingConsensusBases -i in/mapped.qn.bam -o in/fgbio.overlapping.bam -r "$ref" \
  -m fgbio/overlapping_consensus.metrics.txt
samtools sort -o in/fgbio.grouped.sorted.bam in/fgbio.grouped.bam
samtools index in/fgbio.grouped.sorted.bam
align in/fgbio.duplex.bam in/fgbio.duplex.mapped.bam
fgbio ReviewConsensusVariants -i in/variants.vcf -c in/fgbio.duplex.mapped.bam \
  -g in/fgbio.grouped.sorted.bam -r "$ref" -o fgbio/review -s S1 -m 1.0
fgbio EstimateRnaSeqInsertSize -i in/mapped.bam -r in/genes.refflat -p fgbio/rnaseq
fgbio DemuxFastqs -i in/demux_r1.fastq in/demux_r2.fastq -x in/demux.csv -r 8B92T 100T \
  -o in/demux -m fgbio/demux.sample_barcode_metrics.txt --output-type Bam
fgbio EstimatePoolingFractions -v in/pool.vcf -b in/mapped.bam -o fgbio/pooling.fractions.txt
for vcf in called truth; do
  bgzip -f "in/$vcf.vcf"
  tabix -p vcf "in/$vcf.vcf.gz"
done
fgbio AssessPhasing -c in/called.vcf.gz -t in/truth.vcf.gz -o fgbio/phasing
fgbio FindSwitchbackReads -i in/mapped.qn.bam -o in/fgbio.switchback.bam -r "$ref" -m fgbio/switchback
fgbio AssignPrimers -i in/mapped.bam -o in/fgbio.primers.bam -p in/primers.txt \
  -m fgbio/assign_primers.metrics.txt
fgbio CollectErccMetrics -i in/mapped.bam -o fgbio/ercc --custom-mixture in/ercc.txt
# Without --vienna-rna-dir, PickLongIndices predicts no secondary structure and leaves its columns empty.
fgbio PickLongIndices --length 8 --number-of-indices 10 --edit-distance 3 --seed 1 --output fgbio/pick_long_indices.txt

fgumi correct -i in/unmapped.bam -o in/fgumi.corrected.bam -M fgumi/correct.metrics.txt \
  -U in/umis.txt --max-mismatches 1 -d 2
fgumi sort -i in/mapped.bam -o in/mapped.tc.bam --order template-coordinate
fgumi group -i in/mapped.tc.bam -o in/fgumi.grouped.bam -s paired -e 1 -M fgumi/group
fgumi group -i in/mapped.tc.bam -o in/fgumi.grouped.adjacency.bam -s adjacency -e 1
fgumi dedup -i in/mapped.tc.bam -o in/fgumi.dedup.bam -s paired -e 1 -m fgumi/dedup.metrics.txt \
  -H fgumi/dedup.family_sizes.txt --duplication-ladder fgumi/dedup.duplication_ladder.txt \
  --ladder-interval 200
fgumi duplex-metrics -i in/fgumi.grouped.bam -o fgumi/duplex --duplex-umi-counts
fgumi simplex-metrics -i in/fgumi.grouped.adjacency.bam -o fgumi/simplex
fgumi duplex -i in/fgumi.grouped.bam -o in/fgumi.duplex.bam -M 1 -s fgumi/duplex.consensus_stats.txt
fgumi simplex -i in/fgumi.grouped.adjacency.bam -o in/fgumi.simplex.bam -M 1 \
  -s fgumi/simplex.consensus_stats.txt
fgumi codec -i in/fgumi.grouped.bam -o in/fgumi.codec.bam -M 1 -s fgumi/codec.consensus_stats.txt
fgumi filter -i in/fgumi.duplex.bam -o in/fgumi.filtered.bam -r "$ref" -M 1 \
  --stats fgumi/filter.stats.txt
fgumi clip -i in/mapped.qn.bam -o in/fgumi.clipped.bam -r "$ref" --clip-overlapping-reads \
  --clip-bases-past-mate --read-one-five-prime 2 -m fgumi/clip.metrics.txt
fgumi copy-umi -i in/umi_in_name.bam -o in/fgumi.copy_umi.bam -M fgumi/copy_umi.metrics.txt
fgumi retag -i in/fgumi.grouped.bam -o in/fgumi.retag.bam -M fgumi/retag.metrics.txt \
  RX::copy::BX MI::move::XM BX::delete ZZ::delete
fgumi downsample -i in/fgumi.grouped.bam -o in/fgumi.downsampled.bam -f 0.5 --seed 42 \
  --histogram-kept fgumi/downsample.histogram_kept.txt \
  --histogram-rejected fgumi/downsample.histogram_rejected.txt
samtools sort -o in/fgumi.grouped.sorted.bam in/fgumi.grouped.bam
samtools index in/fgumi.grouped.sorted.bam
align in/fgumi.duplex.bam in/fgumi.duplex.mapped.bam
fgumi review -i in/variants.vcf -c in/fgumi.duplex.mapped.bam -g in/fgumi.grouped.sorted.bam \
  -r "$ref" -o fgumi/review -s S1 -m 1.0

find fgbio fgumi \( -name '*.pdf' -o -name '*.bam' -o -name '*.bai' -o -name '*.vcf.gz' \) -delete
gzip -n -c fgbio/group.family_sizes.txt > fgbio/group.family_sizes.txt.gz
gzip -n -c fgumi/correct.metrics.txt > fgumi/correct.metrics.txt.gz
command rm -rf "$repo/tests/data/fgbio" "$repo/tests/data/fgumi"
mkdir -p "$repo/tests/data"
command cp -Rf fgbio fgumi "$repo/tests/data/"
