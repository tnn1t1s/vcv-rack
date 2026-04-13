#include <rack.hpp>
#include <fstream>
#include <atomic>
#include "AgentModule.hpp"

using namespace rack;
extern Plugin* pluginInstance;

/**
 * Inspector -- polls all AgentModule instances in the patch every 30 seconds
 * and writes their current runtime-described state to:
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

        if (mod->model) {
            json_object_set_new(entry, "model_slug", json_string(mod->model->slug.c_str()));
            json_object_set_new(entry, "model_name", json_string(mod->model->name.c_str()));
            if (mod->model->plugin) {
                json_object_set_new(entry, "plugin_slug",
                                    json_string(mod->model->plugin->slug.c_str()));
            }
        }

        json_t* params_out = json_object();
        for (int i = 0; i < (int)mod->params.size(); i++) {
            ParamQuantity* q = mod->getParamQuantity(i);
            std::string name = (q && !q->name.empty())
                ? q->name
                : string::f("PARAM_%d", i);
            json_object_set_new(params_out, name.c_str(), json_real(mod->params[i].getValue()));
        }
        json_object_set_new(entry, "params", params_out);

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
