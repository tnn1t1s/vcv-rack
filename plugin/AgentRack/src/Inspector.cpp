#include <rack.hpp>
#include <fstream>
#include <atomic>
#include "AgentModule.hpp"

using namespace rack;
extern Plugin* pluginInstance;

/**
 * Inspector -- polls all AgentModule instances in the patch each second
 * and writes their manifests + current param values to:
 *   <Rack user dir>/agentrack_state.json
 *
 * The external Python agent reads this file to observe live patch state.
 * File I/O happens in step() (UI thread), never in process() (audio thread).
 *
 * Rack IDs: no params, no ports.
 */
struct Inspector : AgentModule {

    std::atomic<bool> dirty{false};
    float writeTimer = 0.f;
    static constexpr float WRITE_INTERVAL = 30.0f;  // seconds between writes

    Inspector() {
        config(0, 0, 0);
    }

    void process(const ProcessArgs& args) override {
        writeTimer += args.sampleTime;
        if (writeTimer >= WRITE_INTERVAL) {
            writeTimer = 0.f;
            dirty.store(true);
        }
    }

    std::string getManifest() const override {
        return R"({
  "module_id": "agentrack.inspector.v1",
  "ensemble_role": "none",
  "ports": [],
  "params": [],
  "guarantees": [
    "writes agentrack_state.json to Rack user dir every ~1 second",
    "output contains module_id and current param values for all AgentModules in patch"
  ]
})";
    }
};


// ---------------------------------------------------------------------------
// State dump -- called from the UI thread in InspectorWidget::step()
// ---------------------------------------------------------------------------

static void dumpAgentState(int64_t inspectorId) {
    json_t* root = json_object();
    json_object_set_new(root, "timestamp", json_real(system::getTime()));

    json_t* modules_arr = json_array();

    for (int64_t id : APP->engine->getModuleIds()) {
        if (id == inspectorId) continue;  // skip ourselves

        Module* mod = APP->engine->getModule(id);
        if (!mod) continue;

        AgentModule* agent = dynamic_cast<AgentModule*>(mod);
        if (!agent) continue;

        json_t* entry = json_object();
        json_object_set_new(entry, "rack_module_id", json_integer(id));

        // Parse manifest to get module_id and param name -> rack_id mapping
        json_t* manifest = agent->getAgentJson();
        if (manifest) {
            json_t* module_id_j = json_object_get(manifest, "module_id");
            if (module_id_j)
                json_object_set(entry, "module_id", module_id_j);

            json_t* params_out = json_object();
            json_t* params_arr_j = json_object_get(manifest, "params");
            if (params_arr_j && json_is_array(params_arr_j)) {
                size_t i;
                json_t* param;
                json_array_foreach(params_arr_j, i, param) {
                    json_t* name_j    = json_object_get(param, "name");
                    json_t* rack_id_j = json_object_get(param, "rack_id");
                    if (!name_j || !rack_id_j) continue;

                    const char* name = json_string_value(name_j);
                    int rack_id = (int)json_integer_value(rack_id_j);

                    if (rack_id >= 0 && rack_id < (int)mod->params.size()) {
                        float val = mod->params[rack_id].getValue();
                        json_object_set_new(params_out, name, json_real(val));
                    }
                }
            }
            json_object_set_new(entry, "params", params_out);
            json_decref(manifest);
        }

        json_array_append_new(modules_arr, entry);
    }

    json_object_set_new(root, "modules", modules_arr);

    std::string path = asset::user("agentrack_state.json");
    char* str = json_dumps(root, JSON_INDENT(2));
    if (str) {
        std::ofstream f(path);
        f << str;
        free(str);
    }
    json_decref(root);
}


// ---------------------------------------------------------------------------
// Widget -- minimal 2HP panel, drives file writes from UI thread
// ---------------------------------------------------------------------------

struct InspectorPanel : rack::widget::Widget {
    void draw(const DrawArgs& args) override {
        int imgHandle = 0;
        try {
            auto img = APP->window->loadImage(
                asset::plugin(pluginInstance, "res/Inspector-bg.jpg"));
            if (img) imgHandle = img->handle;
        } catch (...) {}

        if (imgHandle > 0) {
            NVGpaint paint = nvgImagePattern(
                args.vg, 0, 0, box.size.x, box.size.y,
                0.f, imgHandle, 1.f);
            nvgBeginPath(args.vg);
            nvgRect(args.vg, 0, 0, box.size.x, box.size.y);
            nvgFillPaint(args.vg, paint);
            nvgFill(args.vg);
        } else {
            nvgBeginPath(args.vg);
            nvgRect(args.vg, 0, 0, box.size.x, box.size.y);
            nvgFillColor(args.vg, nvgRGB(180, 170, 210));
            nvgFill(args.vg);
        }

        // Dark top bar + title
        nvgBeginPath(args.vg);
        nvgRect(args.vg, 0, 0, box.size.x, 20.f);
        nvgFillColor(args.vg, nvgRGBA(0, 0, 0, 170));
        nvgFill(args.vg);

        nvgFontSize(args.vg, 6.5f);
        nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        nvgFillColor(args.vg, nvgRGB(255, 255, 255));
        nvgText(args.vg, box.size.x / 2.f, 10.f, "INSP", NULL);
    }
};


struct InspectorWidget : ModuleWidget {
    InspectorWidget(Inspector* module) {
        setModule(module);

        auto* panel = new InspectorPanel;
        panel->box.size = mm2px(Vec(25.4f, 128.5f));  // 5HP
        addChild(panel);
        box.size = panel->box.size;

        addChild(createWidget<ThemedScrew>(Vec(1 * RACK_GRID_WIDTH, 0)));
        addChild(createWidget<ThemedScrew>(Vec(3 * RACK_GRID_WIDTH, 0)));
        addChild(createWidget<ThemedScrew>(Vec(1 * RACK_GRID_WIDTH, RACK_GRID_HEIGHT - RACK_GRID_WIDTH)));
        addChild(createWidget<ThemedScrew>(Vec(3 * RACK_GRID_WIDTH, RACK_GRID_HEIGHT - RACK_GRID_WIDTH)));
    }

    void step() override {
        ModuleWidget::step();
        auto* m = dynamic_cast<Inspector*>(module);
        if (m && m->dirty.exchange(false)) {
            dumpAgentState(m->id);
        }
    }
};


rack::Model* modelInspector = createModel<Inspector, InspectorWidget>("Inspector");
