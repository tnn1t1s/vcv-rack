/**
 * rack_introspect -- headless VCV Rack module param dumper
 *
 * Loads a plugin dylib, instantiates each requested module with a minimal
 * stubbed rack::Context (no GUI, no audio), and dumps param metadata as JSON.
 *
 * Usage:
 *   rack_introspect <plugin_dir> [ModelSlug ...]
 *
 *   <plugin_dir>  path to the installed plugin directory (contains plugin.dylib
 *                 and plugin.json)
 *   [ModelSlug]   optional list of model slugs to dump; if omitted, dumps all
 *
 * Output (stdout): JSON array of module param descriptors, one object per model:
 *   [{"plugin":"Fundamental","model":"VCO","version":"2.6.4",
 *     "params":[{"id":5,"name":"Pulse width","default":0.5,"min":0.0,"max":1.0}, ...]},
 *    ...]
 *
 * Build: see ../Makefile
 */

#include <dlfcn.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <set>

// Include only the engine/plugin headers -- not the full rack.hpp which
// pulls in GUI dependencies (nanovg, GL, etc.) that we don't have.
#include <common.hpp>
#include <context.hpp>
#include <engine/Module.hpp>
#include <engine/Engine.hpp>
#include <engine/ParamQuantity.hpp>
#include <plugin/Plugin.hpp>
#include <plugin/Model.hpp>

// ---------------------------------------------------------------------------
// Stub context -- modules call APP->engine->getSampleRate() etc.
// We provide a real Engine (from libRack.dylib) so its internal state is
// valid; modules that call engine methods during construction won't crash.
// ---------------------------------------------------------------------------

static rack::Context* make_context() {
    rack::Context* ctx = new rack::Context;
    ctx->engine = new rack::engine::Engine;
    return ctx;
}

// ---------------------------------------------------------------------------
// Plugin init function signature (standard VCV Rack plugin ABI)
// ---------------------------------------------------------------------------

typedef void (*PluginInitFn)(rack::plugin::Plugin*);

// ---------------------------------------------------------------------------
// JSON helpers (minimal, no dependency on jansson for output)
// ---------------------------------------------------------------------------

static std::string json_escape(const std::string& s) {
    std::string out;
    for (char c : s) {
        if (c == '"')  out += "\\\"";
        else if (c == '\\') out += "\\\\";
        else if (c == '\n') out += "\\n";
        else           out += c;
    }
    return out;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

int main(int argc, char** argv) {
    if (argc < 2) {
        fprintf(stderr, "Usage: rack_introspect <plugin_dir> [ModelSlug ...]\n");
        return 1;
    }

    const char* plugin_dir = argv[1];

    // Optional filter set
    std::set<std::string> filter;
    for (int i = 2; i < argc; i++)
        filter.insert(argv[i]);

    // Set up stub context so APP-> calls don't crash
    rack::contextSet(make_context());

    // Load plugin dylib
    std::string dylib_path = std::string(plugin_dir) + "/plugin.dylib";
    void* handle = dlopen(dylib_path.c_str(), RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        fprintf(stderr, "dlopen failed: %s\n", dlerror());
        return 1;
    }

    // Call plugin init
    PluginInitFn init_fn = (PluginInitFn) dlsym(handle, "init");
    if (!init_fn) {
        fprintf(stderr, "No init() symbol in %s\n", dylib_path.c_str());
        return 1;
    }

    rack::plugin::Plugin* plugin = new rack::plugin::Plugin;
    plugin->path = plugin_dir;

    // Read slug and version from plugin.json (init() doesn't populate these)
    std::string json_path = std::string(plugin_dir) + "/plugin.json";
    if (FILE* jf = fopen(json_path.c_str(), "r")) {
        // Minimal parse: just grab "slug" and "version" values
        char buf[8192]; size_t n = fread(buf, 1, sizeof(buf)-1, jf); buf[n] = 0;
        fclose(jf);
        auto grab = [&](const char* key) -> std::string {
            std::string k = std::string("\"") + key + "\"";
            const char* p = strstr(buf, k.c_str());
            if (!p) return "";
            p = strchr(p, ':'); if (!p) return "";
            p = strchr(p, '"'); if (!p) return "";
            p++;
            const char* e = strchr(p, '"'); if (!e) return "";
            return std::string(p, e);
        };
        plugin->slug    = grab("slug");
        plugin->version = grab("version");
    }

    init_fn(plugin);

    // Emit JSON
    bool first_model = true;
    printf("[\n");

    for (rack::plugin::Model* model : plugin->models) {
        if (!filter.empty() && filter.find(model->slug) == filter.end())
            continue;

        // Instantiate the module -- this runs the constructor and all configParam calls
        rack::engine::Module* mod = nullptr;
        try {
            mod = model->createModule();
        } catch (...) {
            fprintf(stderr, "Warning: %s/%s threw during createModule(), skipping\n",
                    plugin->slug.c_str(), model->slug.c_str());
            continue;
        }

        if (!mod) {
            fprintf(stderr, "Warning: %s/%s returned null module, skipping\n",
                    plugin->slug.c_str(), model->slug.c_str());
            continue;
        }

        if (!first_model) printf(",\n");
        first_model = false;

        printf("  {\n");
        printf("    \"plugin\": \"%s\",\n",  json_escape(plugin->slug).c_str());
        printf("    \"model\": \"%s\",\n",   json_escape(model->slug).c_str());
        printf("    \"version\": \"%s\",\n", json_escape(plugin->version).c_str());
        printf("    \"params\": [\n");

        bool first_param = true;
        for (int i = 0; i < (int) mod->paramQuantities.size(); i++) {
            rack::engine::ParamQuantity* pq = mod->paramQuantities[i];
            if (!pq) continue;

            if (!first_param) printf(",\n");
            first_param = false;

            printf("      {\"id\": %d, \"name\": \"%s\", "
                   "\"default\": %g, \"min\": %g, \"max\": %g}",
                   i,
                   json_escape(pq->name).c_str(),
                   (double) pq->defaultValue,
                   (double) pq->minValue,
                   (double) pq->maxValue);
        }

        printf("\n    ]\n  }");

        delete mod;
    }

    printf("\n]\n");

    delete plugin;
    dlclose(handle);
    return 0;
}
