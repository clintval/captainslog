import htsjdk.samtools.metrics.MetricsFile;
import java.io.File;
import java.util.Arrays;

/** Checks that htsjdk reads each file written into a directory as the metrics and histogram of its fixture. */
public class ReadBack {
    public static void main(final String[] args) {
        if (args.length != 2) {
            System.err.println("Usage: java -cp picard.jar ReadBack.java <fixtures_dir> <written_dir>");
            System.exit(2);
        }
        final File fixtures = new File(args[0]);
        final File[] written = new File(args[1]).listFiles(File::isFile);
        if (written == null || written.length == 0) {
            System.out.println("No files to read in " + args[1]);
            System.exit(1);
        }
        Arrays.sort(written);
        int failures = 0;
        for (final File file : written) {
            final File fixture = new File(fixtures, file.getName());
            try {
                if (!MetricsFile.areMetricsAndHistogramsEqual(fixture, file)) {
                    System.out.println("Differs from its fixture: " + file);
                    failures++;
                }
            } catch (final RuntimeException e) {
                System.out.println("Failed to read: " + file + ": " + e);
                failures++;
            }
        }
        System.out.printf("%d of %d files read back as their fixtures.%n", written.length - failures, written.length);
        System.exit(failures == 0 ? 0 : 1);
    }
}
