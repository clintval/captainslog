import com.fulcrumgenomics.util.Metric;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.jar.JarEntry;
import java.util.jar.JarFile;

/** Prints, as JSON, fgbio's metrics classes, the columns `Metric.write` writes for each, and their enumerations. */
public class FgbioSchema {
    public static void main(final String[] args) throws Exception {
        final List<Class<?>> classes = new ArrayList<>();
        final String version;
        try (JarFile jar = new JarFile(args[0])) {
            version = jar.getManifest().getMainAttributes().getValue("Implementation-Version");
            for (final JarEntry entry : Collections.list(jar.entries())) {
                final String path = entry.getName();
                if (!path.startsWith("com/fulcrumgenomics/") || !path.endsWith(".class")) continue;
                final String name = path.substring(0, path.length() - ".class".length()).replace('/', '.');
                final Class<?> type;
                try {
                    type = Class.forName(name, false, FgbioSchema.class.getClassLoader());
                } catch (final Throwable ignored) {
                    continue;
                }
                if (isMetricsClass(type)) classes.add(type);
            }
        }
        classes.sort((left, right) -> left.getName().compareTo(right.getName()));

        final var universe = scala.reflect.runtime.package$.MODULE$.universe();
        final var mirror = universe.runtimeMirror(FgbioSchema.class.getClassLoader());
        final Map<String, List<String>> enums = new TreeMap<>();
        final List<String> entries = new ArrayList<>();
        for (final Class<?> type : classes) {
            final var symbol = mirror.classSymbol(type);
            final List<String> columns = new ArrayList<>();
            // Metric.names reads the parameters of the primary constructor, which are the columns in order.
            final var params = symbol.primaryConstructor().asMethod().paramLists().head();
            for (int i = 0; i < params.length(); i++) {
                final var param = params.apply(i);
                final var declared = param.typeSignature();
                final String typeName = declared.dealias().toString();
                Class<?> erased = Object.class;
                try {
                    erased = (Class<?>) mirror.runtimeClass(declared.typeSymbol().asClass());
                } catch (final Throwable ignored) {
                    // scala.Any and other types with no class of their own.
                }
                if (isEnumeration(erased)) enums.put(erased.getName(), entryNames(erased));
                final var optional = declared.dealias().typeArgs();
                if (!optional.isEmpty()) {
                    try {
                        final Class<?> inner = (Class<?>) mirror.runtimeClass(optional.head().typeSymbol().asClass());
                        if (isEnumeration(inner)) enums.put(inner.getName(), entryNames(inner));
                    } catch (final Throwable ignored) {
                        // As above.
                    }
                }
                columns.add(String.format(
                        "        {\"name\": %s, \"type\": %s, \"alias\": %s, \"class\": %s}",
                        quote(param.name().decodedName().toString()), quote(typeName),
                        quote(declared.toString()), quote(erased.getName())));
            }
            entries.add(String.format(
                    "    {\"class\": %s,%n     \"fields\": [%n%s%n     ]}",
                    quote(type.getName()), String.join(",\n", columns)));
        }

        final List<String> enumEntries = new ArrayList<>();
        for (final Map.Entry<String, List<String>> entry : enums.entrySet()) {
            final List<String> names = entry.getValue().stream().map(FgbioSchema::quote).toList();
            enumEntries.add(String.format("    %s: [%s]", quote(entry.getKey()), String.join(", ", names)));
        }

        System.out.printf("{\"fgbio\": %s,%n", quote(version));
        System.out.printf(" \"classes\": [%n%s%n ],%n", String.join(",\n", entries));
        System.out.printf(" \"enums\": {%n%s%n }}%n", String.join(",\n", enumEntries));
    }

    private static boolean isMetricsClass(final Class<?> type) {
        final int modifiers = type.getModifiers();
        return Metric.class.isAssignableFrom(type) && type != Metric.class && Modifier.isPublic(modifiers)
                && !Modifier.isAbstract(modifiers) && !type.isInterface() && !type.getName().endsWith("$");
    }

    private static boolean isEnumeration(final Class<?> type) {
        return enumeratum.EnumEntry.class.isAssignableFrom(type) || type.isEnum();
    }

    /** The texts fgbio writes for an enumeration: enumeratum's entry names, or a Java enum's constant names. */
    private static List<String> entryNames(final Class<?> type) throws Exception {
        final List<String> names = new ArrayList<>();
        if (type.isEnum()) {
            for (final Object constant : type.getEnumConstants()) names.add(((Enum<?>) constant).name());
            return names;
        }
        final Class<?> companion = Class.forName(type.getName() + "$", true, FgbioSchema.class.getClassLoader());
        final Object module = companion.getField("MODULE$").get(null);
        final Method values = companion.getMethod("values");
        final scala.collection.Iterable<?> entries = (scala.collection.Iterable<?>) values.invoke(module);
        final var iterator = entries.iterator();
        while (iterator.hasNext()) names.add(((enumeratum.EnumEntry) iterator.next()).entryName());
        return names;
    }

    private static String quote(final String text) {
        return "\"" + text.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
    }
}
