#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
work="$(mktemp -d)"
trap 'command rm -rf "$work"' EXIT
cd "$work"
mkdir in picard riker

testdata="broadinstitute/picard/3.5.0/testdata/picard"

fetch() {
  local file
  file="in/$(basename "$1")"
  curl -fsSL --retry 3 -o "$file" "https://raw.githubusercontent.com/$testdata/$1"
  if head -c 64 "$file" | grep -q '^version https://git-lfs'; then
    curl -fsSL --retry 3 -o "$file" "https://media.githubusercontent.com/media/$testdata/$1"
  fi
  if head -c 64 "$file" | grep -q '^version https://git-lfs'; then
    echo "Fetched a Git LFS pointer instead of $1" >&2
    exit 1
  fi
}

fetch fingerprint/reference.shifted.for.crams.fasta
fetch fingerprint/reference.shifted.for.crams.dict
fetch fingerprint/Homo_sapiens_assembly19.haplotype_database.subset.shifted.for.crams.txt
fetch fingerprint/NA12891.over.fingerprints.shifted.for.crams.r1.sam
fetch fingerprint/NA12891.over.fingerprints.shifted.for.crams.r2.sam
fetch fingerprint/NA12892.over.fingerprints.shifted.for.crams.r1.sam
fetch fingerprint/NA12891.over.fingerprints.r1.sam
fetch fingerprint/NA12891.fp.vcf
fetch fingerprint/Homo_sapiens_assembly19.haplotype_database.subset.txt
fetch sam/rna_seq_metrics.refflat
fetch sam/rna_seq_metrics.interval_list
fetch sam/CollectRrbsMetrics/input.sam
fetch reference/test.fasta
fetch reference/test.fasta.fai
fetch reference/test.dict
fetch vcf/mini.vcf
fetch vcf/mini.vcf.idx
fetch vcf/mini.dbsnp.vcf
fetch vcf/mini.dbsnp.vcf.idx
fetch vcf/CEUTrio-snps.vcf

ref=in/reference.shifted.for.crams.fasta
dict=in/reference.shifted.for.crams.dict
sites=in/Homo_sapiens_assembly19.haplotype_database.subset.shifted.for.crams.txt
bam=in/sample.bam
samtools faidx "$ref"

# One read group per input file, so the sample has two libraries and two read groups.
libraries=(Pond-492101 NormPond-544932)
for n in 1 2; do
  samtools view -h "in/NA12891.over.fingerprints.shifted.for.crams.r$n.sam" \
    | grep -v '^@RG' \
    | samtools addreplacerg -m overwrite_all -O bam -o "in/r$n.bam" \
      -r "@RG\tID:NA12891.r$n\tSM:NA12891\tLB:${libraries[n - 1]}\tPL:ILLUMINA\tPU:NA12891.r$n" -
done
samtools merge -o in/merged.bam in/r1.bam in/r2.bam

{ cat "$dict"; awk -v OFS='\t' '!/^[@#]/ {print $1, $2 - 50, $2 + 49, "+", $3}' "$sites"; } > in/targets.interval_list
{ cat "$dict"; awk -v OFS='\t' '!/^[@#]/ {print $1, $2 - 100, $2 + 99, "+", $3}' "$sites"; } > in/baits.interval_list
awk 'BEGIN {FS = OFS = "\t"} {sub(/^chr/, "", $3); print}' in/rna_seq_metrics.refflat > in/genes.refflat
{ cat "$dict"; awk 'BEGIN {FS = OFS = "\t"} !/^@/ {sub(/^chr/, "", $1); print}' in/rna_seq_metrics.interval_list; } > in/ribosomal.interval_list

levels=(
  METRIC_ACCUMULATION_LEVEL=ALL_READS
  METRIC_ACCUMULATION_LEVEL=SAMPLE
  METRIC_ACCUMULATION_LEVEL=LIBRARY
  METRIC_ACCUMULATION_LEVEL=READ_GROUP
)

picard MarkDuplicates I=in/merged.bam O="$bam" M=picard/dup.duplication_metrics
samtools index "$bam"
picard MarkDuplicates I=in/r1.bam O=in/r1.marked.bam M=picard/one_library.duplication_metrics

picard CollectMultipleMetrics I="$bam" O=picard/cmm R="$ref" "${levels[@]}" \
  PROGRAM=null \
  PROGRAM=CollectAlignmentSummaryMetrics \
  PROGRAM=CollectBaseDistributionByCycle \
  PROGRAM=CollectGcBiasMetrics \
  PROGRAM=CollectInsertSizeMetrics \
  PROGRAM=CollectQualityYieldMetrics \
  PROGRAM=CollectSequencingArtifactMetrics \
  PROGRAM=MeanQualityByCycle \
  PROGRAM=QualityScoreDistribution
# Picard 3.5.0 shares target depth histograms across levels and throws on any level but ALL_READS.
picard CollectHsMetrics I="$bam" O=picard/hs.hs_metrics R="$ref" \
  BAIT_INTERVALS=in/baits.interval_list \
  TARGET_INTERVALS=in/targets.interval_list \
  PER_TARGET_COVERAGE=picard/hs.per_target_coverage.txt \
  PER_BASE_COVERAGE=picard/hs.per_base_coverage.txt
picard CollectTargetedPcrMetrics I="$bam" O=picard/pcr.targeted_pcr_metrics R="$ref" \
  AMPLICON_INTERVALS=in/baits.interval_list \
  TARGET_INTERVALS=in/targets.interval_list
picard CollectWgsMetrics I="$bam" O=picard/wgs.wgs_metrics R="$ref"
picard CollectRawWgsMetrics I="$bam" O=picard/raw.raw_wgs_metrics R="$ref" COVERAGE_CAP=250
picard CollectWgsMetricsWithNonZeroCoverage I="$bam" O=picard/nonzero.wgs_metrics R="$ref" \
  CHART=picard/nonzero.wgs_metrics.pdf
picard CollectRnaSeqMetrics I="$bam" O=picard/rna.rna_metrics "${levels[@]}" \
  REF_FLAT=in/genes.refflat \
  RIBOSOMAL_INTERVALS=in/ribosomal.interval_list \
  STRAND_SPECIFICITY=NONE \
  MINIMUM_LENGTH=100
picard CollectOxoGMetrics I="$bam" O=picard/oxog.oxog_metrics R="$ref"
picard EstimateLibraryComplexity I="$bam" O=picard/elc.duplication_metrics
picard CollectJumpingLibraryMetrics I="$bam" O=picard/jump.jumping_metrics
picard CrosscheckFingerprints O=picard/crosscheck.crosscheck_metrics HAPLOTYPE_MAP="$sites" \
  I="$bam" \
  I=in/NA12892.over.fingerprints.shifted.for.crams.r1.sam \
  CROSSCHECK_BY=LIBRARY
picard CheckFingerprint O=picard/fingerprint \
  I=in/NA12891.over.fingerprints.r1.sam \
  GENOTYPES=in/NA12891.fp.vcf \
  HAPLOTYPE_MAP=in/Homo_sapiens_assembly19.haplotype_database.subset.txt
picard CollectRrbsMetrics I=in/input.sam M=picard/rrbs R=in/test.fasta "${levels[@]}"
picard CollectVariantCallingMetrics I=in/mini.vcf DBSNP=in/mini.dbsnp.vcf O=picard/vc
picard GenotypeConcordance O=picard/concordance \
  TRUTH_VCF=in/CEUTrio-snps.vcf TRUTH_SAMPLE=NA12878 \
  CALL_VCF=in/CEUTrio-snps.vcf CALL_SAMPLE=NA12891

# riker multi requires the error stratifiers although its help gives them as the default.
riker multi -i "$bam" -o riker/s -r "$ref" \
  --tools alignment basic error gcbias hybcap isize rna wgs \
  --error::reference "$ref" \
  --error::stratify-by bq isize gc strand pair_orientation hp_len cycle read_num read_num,cycle \
    read_num,hp_len read_num,gc read_num,pre_dinuc mapq nm context_3bp \
  --hybcap::baits in/baits.interval_list \
  --hybcap::targets in/targets.interval_list \
  --hybcap::per-target-coverage \
  --hybcap::per-base-coverage \
  --rna::gene-model in/genes.refflat \
  --rna::ribosomal-intervals in/ribosomal.interval_list

find picard riker \( -name '*.pdf' -o -name '*.bw' \) -delete
command rm -rf "$repo/tests/data/picard" "$repo/tests/data/riker"
mkdir -p "$repo/tests/data"
command cp -Rf picard riker "$repo/tests/data/"
