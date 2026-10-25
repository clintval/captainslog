import htsjdk.samtools.metrics.MetricBase;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.jar.JarEntry;
import java.util.jar.JarFile;

/** Prints, as JSON, Picard's metrics classes, the columns htsjdk writes for each, and their enums. */
public class PicardSchema {
    public static void main(final String[] args) throws Exception {
        final List<Class<?>> classes = new ArrayList<>();
        final String version;
        try (JarFile jar = new JarFile(args[0])) {
            version = jar.getManifest().getMainAttributes().getValue("Implementation-Version");
            for (final JarEntry entry : Collections.list(jar.entries())) {
                final String path = entry.getName();
                if (!path.startsWith("picard/") || !path.endsWith(".class")) continue;
                final String name = path.substring(0, path.length() - ".class".length()).replace('/', '.');
                final Class<?> type = Class.forName(name, false, PicardSchema.class.getClassLoader());
                if (isMetricsClass(type)) classes.add(type);
            }
        }
        classes.sort((left, right) -> left.getName().compareTo(right.getName()));

        final Map<String, List<String>> enums = new TreeMap<>();
        final List<String> entries = new ArrayList<>();
        for (final Class<?> type : classes) {
            final List<String> columns = new ArrayList<>();
            // MetricsFile.printBeanMetrics writes one column per field of getBeanType().getFields().
            for (final Field field : type.getFields()) {
                final Class<?> kind = field.getType();
                if (kind.isEnum()) enums.put(kind.getName(), constants(kind));
                columns.add(String.format(
                        "        {\"name\": %s, \"type\": %s, \"declared_by\": %s}",
                        quote(field.getName()), quote(kind.getName()), quote(field.getDeclaringClass().getName())));
            }
            entries.add(String.format(
                    "    {\"class\": %s,%n     \"fields\": [%n%s%n     ]}",
                    quote(type.getName()), String.join(",\n", columns)));
        }

        final List<String> enumEntries = new ArrayList<>();
        for (final Map.Entry<String, List<String>> entry : enums.entrySet()) {
            final List<String> names = entry.getValue().stream().map(PicardSchema::quote).toList();
            enumEntries.add(String.format("    %s: [%s]", quote(entry.getKey()), String.join(", ", names)));
        }

        System.out.printf("{\"picard\": %s,%n", quote(version));
        System.out.printf(" \"classes\": [%n%s%n ],%n", String.join(",\n", entries));
        System.out.printf(" \"enums\": {%n%s%n }}%n", String.join(",\n", enumEntries));
    }

    private static boolean isMetricsClass(final Class<?> type) {
        final int modifiers = type.getModifiers();
        return MetricBase.class.isAssignableFrom(type) && Modifier.isPublic(modifiers) && !Modifier.isAbstract(modifiers);
    }

    private static List<String> constants(final Class<?> kind) {
        final List<String> names = new ArrayList<>();
        for (final Object constant : kind.getEnumConstants()) names.add(((Enum<?>) constant).name());
        return names;
    }

    private static String quote(final String text) {
        return "\"" + text.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
    }
}
