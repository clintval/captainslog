"""Write a small, seeded set of duplex UMI reads and the inputs fgumi and fgbio need beside them.

Every molecule is a fragment of a random reference, read on both strands as in duplex sequencing:
the A strand's templates carry the UMI pair `X-Y` with read one on the forward strand, and the B
strand's carry `Y-X` with read one on the reverse strand. Family sizes vary, some molecules are
read on one strand only, some UMIs carry errors, and some fragments are shorter than a read so
that it reads into the adapter. Each molecule comes from one of two pooled samples, whose
genotypes at a set of SNPs it carries.
"""

import argparse
import random
from dataclasses import dataclass
from pathlib import Path

READ_LENGTH = 100
CONTIGS = {"chr1": 20_000, "chr2": 8_000, "ERCC-00130": 1_000, "ERCC-00004": 600}
SAMPLES = {"S1": 0.7, "S2": 0.3}
SAMPLE_BARCODES = {"S1": "AAACCCGG", "S2": "TTTGGGCC"}
AMPLICONS = [("chr2", 1_000, 1_019, 1_180, 1_199), ("chr2", 3_000, 3_019, 3_230, 3_249)]
ADAPTER = "AGATCGGAAGAGCACACGTCTGAACTCCAGTCAC" * 3
COMPLEMENT = str.maketrans("ACGTN", "TGCAN")

Sites = dict[tuple[str, int], tuple[str, str]]


@dataclass
class Molecule:
    """A fragment of the reference, with its UMI pair, its sample, and the reads of each strand."""

    contig: str
    start: int
    length: int
    umis: tuple[str, str]
    sample: str
    sizes: tuple[int, int]


@dataclass
class Read:
    """One end of a template as it aligns: its flag, 1-based position, CIGAR, and bases."""

    flag: int
    pos: int
    cigar: str
    seq: str
    quals: str

    @property
    def is_reverse(self) -> bool:
        """Whether the read aligns to the reverse strand."""
        return bool(self.flag & 16)


def revcomp(seq: str) -> str:
    """The reverse complement of a sequence."""
    return seq.translate(COMPLEMENT)[::-1]


def distance(left: str, right: str) -> int:
    """The number of mismatches between two sequences of the same length."""
    return sum(a != b for a, b in zip(left, right, strict=True))


def whitelist(rng: random.Random, count: int = 24, length: int = 8) -> list[str]:
    """UMIs at least three mismatches apart, so one error is always correctable."""
    umis: list[str] = []
    while len(umis) < count:
        umi = "".join(rng.choice("ACGT") for _ in range(length))
        if all(distance(umi, other) >= 3 for other in umis):
            umis.append(umi)
    return umis


def mutate(rng: random.Random, umi: str, edits: int) -> str:
    """A sequence with this many of its bases changed."""
    bases = list(umi)
    for index in rng.sample(range(len(bases)), edits):
        bases[index] = rng.choice([b for b in "ACGT" if b != bases[index]])
    return "".join(bases)


def observed_umi(rng: random.Random, first: str, second: str) -> str:
    """The UMI pair as read: usually exact, sometimes with one, three, or all bases wrong."""
    roll = rng.random()
    if roll < 0.06:
        first = mutate(rng, first, 1)
    elif roll < 0.07:
        second = mutate(rng, second, 3)
    elif roll < 0.075:
        first = "N" * len(first)
    return f"{first}-{second}"


def family_size(rng: random.Random) -> int:
    """The number of templates read from one strand of a molecule."""
    return min(1 + int(rng.expovariate(1 / 2.5)), 12)


def molecules(rng: random.Random, umis: list[str]) -> list[Molecule]:
    """Random molecules on the chromosomes, plus some on each amplicon and ERCC transcript."""
    found: list[Molecule] = []

    def add(contig: str, start: int, length: int, single: bool = False) -> None:
        pair = rng.sample(umis, 2)
        sample = rng.choices(list(SAMPLES), weights=list(SAMPLES.values()))[0]
        sizes = (family_size(rng), 0 if single else family_size(rng))
        found.append(Molecule(contig, start, length, (pair[0], pair[1]), sample, sizes))

    for _ in range(320):
        contig = rng.choices(["chr1", "chr2"], weights=[20, 8])[0]
        length = rng.randint(75, 99) if rng.random() < 0.05 else rng.randint(120, 320)
        add(contig, rng.randint(0, CONTIGS[contig] - length), length, single=rng.random() < 0.15)
    for contig, left_start, _, _, right_end in AMPLICONS:
        for _ in range(6):
            add(contig, left_start - 1, right_end - left_start + 1)
    for contig in ("ERCC-00130", "ERCC-00004"):
        for _ in range(8 if contig == "ERCC-00130" else 3):
            length = rng.randint(120, 250)
            add(contig, rng.randint(0, CONTIGS[contig] - length), length)
    return found


def snps(rng: random.Random, reference: dict[str, str]) -> Sites:
    """Twenty SNPs on chr1, as (contig, 0-based position) to (ref, alt)."""
    sites: Sites = {}
    for position in range(500, 19_500, 950):
        ref = reference["chr1"][position]
        sites[("chr1", position)] = (ref, rng.choice([b for b in "ACGT" if b != ref]))
    return sites


def genotype(sample: str, index: int) -> str:
    """S1 is homozygous alternate at even SNPs, and S2 at odd ones."""
    return "1/1" if (index % 2 == 0) == (sample == "S1") else "0/0"


def with_errors(rng: random.Random, seq: str) -> tuple[str, str]:
    """A read of a sequence with rare substitution errors, and its base qualities."""
    bases: list[str] = list(seq)
    quals: list[str] = []
    for index in range(len(bases)):
        qual = rng.choice("IIIIIIII5+")
        if rng.random() < 0.004 and bases[index] != "N":
            bases[index] = rng.choice([b for b in "ACGT" if b != bases[index]])
            qual = "5"
        quals.append(qual)
    return "".join(bases), "".join(quals)


def top_strand(molecule: Molecule, reference: dict[str, str], sites: Sites) -> str:
    """The molecule's top strand, carrying its sample's alternate alleles."""
    end = molecule.start + molecule.length
    fragment = list(reference[molecule.contig][molecule.start : end])
    for index, ((contig, position), (_, alt)) in enumerate(sites.items()):
        inside = contig == molecule.contig and molecule.start <= position < end
        if inside and genotype(molecule.sample, index) == "1/1":
            fragment[position - molecule.start] = alt
    return "".join(fragment)


def sam_lines(name: str, molecule: Molecule, umi: str, ends: tuple[Read, Read]) -> list[str]:
    """The mapped SAM line of each end of a template, read one first."""
    lines: list[str] = []
    for this, mate in (ends, ends[::-1]):
        leftmost = this.pos == min(ends[0].pos, ends[1].pos) and not this.is_reverse
        tlen = molecule.length if leftmost else -molecule.length
        tags = [f"RG:Z:{molecule.sample}", f"RX:Z:{umi}", f"MC:Z:{mate.cigar}", "MQ:i:60"]
        fields = [name, str(this.flag), molecule.contig, str(this.pos), "60", this.cigar, "="]
        fields += [str(mate.pos), str(tlen), this.seq, this.quals, *tags]
        lines.append("\t".join(fields))
    return lines


def unmapped_lines(name: str, sample: str, umi: str, ends: tuple[Read, Read]) -> list[str]:
    """The unmapped SAM line of each end of a template, in sequencing order."""
    lines: list[str] = []
    for end in ends:
        flag = 77 if end.flag & 64 else 141
        seq, quals = (revcomp(end.seq), end.quals[::-1]) if end.is_reverse else (end.seq, end.quals)
        fields = [name, str(flag), "*", "0", "0", "*", "*", "0", "0", seq, quals]
        lines.append("\t".join([*fields, f"RG:Z:{sample}", f"RX:Z:{umi}"]))
    return lines


def records(
    rng: random.Random, found: list[Molecule], reference: dict[str, str], sites: Sites
) -> list[tuple[list[str], list[str]]]:
    """Each template as (mapped SAM lines, unmapped SAM lines), read one then read two."""
    templates: list[tuple[list[str], list[str]]] = []
    for number, molecule in enumerate(found):
        top = top_strand(molecule, reference, sites)
        span = min(molecule.length, READ_LENGTH)
        clip = READ_LENGTH - span
        forward_seq = top[:span] + ADAPTER[:clip]
        reverse_seq = revcomp(ADAPTER[:clip]) + top[-span:]
        forward_cigar = f"{span}M{clip}S" if clip else f"{span}M"
        reverse_cigar = f"{clip}S{span}M" if clip else f"{span}M"
        forward_pos = molecule.start + 1
        reverse_pos = molecule.start + molecule.length - span + 1
        x, y = molecule.umis
        for strand, size in zip("AB", molecule.sizes, strict=True):
            for copy in range(size):
                name = f"sim:{number}:{strand}{copy}"
                umi = observed_umi(rng, x, y) if strand == "A" else observed_umi(rng, y, x)
                forward = Read(0, forward_pos, forward_cigar, *with_errors(rng, forward_seq))
                reverse = Read(0, reverse_pos, reverse_cigar, *with_errors(rng, reverse_seq))
                if strand == "A":
                    forward.flag, reverse.flag = 99, 147
                    ends = (forward, reverse)
                else:
                    reverse.flag, forward.flag = 83, 163
                    ends = (reverse, forward)
                mapped = sam_lines(name, molecule, umi, ends)
                templates.append((mapped, unmapped_lines(name, molecule.sample, umi, ends)))
    return templates


def sam_header(sort_order: str) -> list[str]:
    """A SAM header with the reference's contigs and one read group per sample."""
    lines = [f"@HD\tVN:1.6\tSO:{sort_order}"]
    lines += [f"@SQ\tSN:{name}\tLN:{length}" for name, length in CONTIGS.items()]
    lines += [f"@RG\tID:{sample}\tSM:{sample}\tLB:{sample}-lib\tPL:ILLUMINA" for sample in SAMPLES]
    return lines


def vcf_header(samples: list[str], phased: bool = False) -> list[str]:
    """A VCF header with the reference's contigs, and a phase set field when phased."""
    lines = ["##fileformat=VCFv4.2"]
    lines += [f"##contig=<ID={name},length={length}>" for name, length in CONTIGS.items()]
    lines += ['##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">']
    lines += ['##FORMAT=<ID=GQ,Number=1,Type=Integer,Description="Genotype quality">']
    if phased:
        lines += ['##FORMAT=<ID=PS,Number=1,Type=Integer,Description="Phase set">']
    columns = ["#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO", "FORMAT", *samples]
    return [*lines, "\t".join(columns)]


def write_lines(path: Path, lines: list[str]) -> None:
    """Write each line, ending each with a newline."""
    _ = path.write_text("".join(f"{line}\n" for line in lines))


def write_reads(out: Path, templates: list[tuple[list[str], list[str]]]) -> None:
    """Write the mapped, unmapped, and UMI-in-name SAMs."""
    write_lines(
        out / "mapped.sam",
        [*sam_header("unsorted"), *(line for lines, _ in templates for line in lines)],
    )
    unmapped = [line for _, lines in templates for line in lines]
    write_lines(out / "unmapped.sam", [*sam_header("queryname"), *unmapped])
    named: list[str] = []
    for _, lines in templates[:200]:
        for line in lines:
            fields = line.split("\t")
            umi = fields[-1].removeprefix("RX:Z:").replace("-", "+")
            named.append("\t".join([f"{fields[0]}:{umi}", *fields[1:-1]]))
    write_lines(out / "umi_in_name.sam", [*sam_header("unsorted"), *named])


def write_variants(out: Path, sites: Sites) -> None:
    """Write the VCFs to review, to estimate pooling fractions from, and to assess phasing with."""
    order = list(sites)
    review = [
        f"{contig}\t{position + 1}\t.\t{sites[(contig, position)][0]}\t"
        + f"{sites[(contig, position)][1]}\t.\tPASS\t.\tGT\t0/1"
        for contig, position in order[:2]
    ]
    write_lines(out / "variants.vcf", [*vcf_header(["S1"]), *review])
    pool: list[str] = []
    for index, (contig, position) in enumerate(order):
        ref, alt = sites[(contig, position)]
        calls = [f"{genotype(sample, index)}:99" for sample in SAMPLES]
        pool.append(
            "\t".join([contig, str(position + 1), ".", ref, alt, ".", "PASS", ".", "GT:GQ"])
        )
        pool[-1] += "\t" + "\t".join(calls)
    write_lines(out / "pool.vcf", [*vcf_header(list(SAMPLES)), *pool])
    flipped: dict[str, set[int]] = {"truth": set(), "called": {6, 13}}
    for name, flips in flipped.items():
        phased: list[str] = []
        for index, (contig, position) in enumerate(order):
            ref, alt = sites[(contig, position)]
            gt = "1|0" if (index % 3 == 0) != (index in flips) else "0|1"
            block = order[0] if name == "truth" or index < 10 else order[10]
            fields = [contig, str(position + 1), ".", ref, alt, ".", "PASS", ".", "GT:GQ:PS"]
            phased.append("\t".join([*fields, f"{gt}:99:{block[1] + 1}"]))
        write_lines(out / f"{name}.vcf", [*vcf_header(["S1"], phased=True), *phased])


def write_annotations(out: Path) -> None:
    """Write the gene model, the ERCC mixture, and the amplicons."""
    write_lines(
        out / "genes.refflat",
        [
            "GENE1\tTX1\tchr1\t+\t0\t20000\t0\t20000\t2\t0,10500,\t10000,20000,",
            "GENE2\tTX2\tchr2\t-\t0\t8000\t0\t8000\t1\t0,\t8000,",
        ],
    )
    write_lines(
        out / "ercc.txt", ["ercc_id\tconcentration", "ERCC-00130\t30000", "ERCC-00004\t7500"]
    )
    amplicons = ["\t".join(map(str, amplicon)) for amplicon in AMPLICONS]
    write_lines(
        out / "primers.txt", ["chrom\tleft_start\tleft_end\tright_start\tright_end", *amplicons]
    )


def write_demux(
    rng: random.Random, out: Path, templates: list[tuple[list[str], list[str]]]
) -> None:
    """Write FASTQs whose read one starts with a sample barcode, and the samples' metadata."""
    samples = [f"{s},{s},{s}-lib,simulated,{b}" for s, b in SAMPLE_BARCODES.items()]
    write_lines(
        out / "demux.csv", ["Sample_ID,Sample_Name,Library_ID,Description,Sample_Barcode", *samples]
    )
    r1: list[str] = []
    r2: list[str] = []
    for count, (_, unmapped) in enumerate(templates[:300]):
        first, second = (line.split("\t") for line in unmapped)
        sample = first[11].removeprefix("RG:Z:")
        barcode = SAMPLE_BARCODES[sample] if count % 25 else "GGGGGGGG"
        if count % 10 == 0:
            barcode = mutate(rng, barcode, 1)
        r1 += [f"@{first[0]}", f"{barcode}{first[9][8:]}", "+", f"{'I' * 8}{first[10][8:]}"]
        r2 += [f"@{second[0]}", second[9], "+", second[10]]
    write_lines(out / "demux_r1.fastq", r1)
    write_lines(out / "demux_r2.fastq", r2)


def main() -> None:
    """Write the reference, the reads, and every other input into one directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("output", type=Path, help="the directory to write into")
    _ = parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    out: Path = args.output
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    reference = {
        name: "".join(rng.choice("ACGT") for _ in range(length)) for name, length in CONTIGS.items()
    }
    fasta: list[str] = []
    for name, seq in reference.items():
        fasta += [f">{name}", *(seq[i : i + 60] for i in range(0, len(seq), 60))]
    write_lines(out / "ref.fasta", fasta)

    umis = whitelist(rng)
    write_lines(out / "umis.txt", umis)
    sites = snps(rng, reference)
    templates = records(rng, molecules(rng, umis), reference, sites)
    write_reads(out, templates)
    write_variants(out, sites)
    write_annotations(out)
    write_demux(rng, out, templates)


if __name__ == "__main__":
    main()
