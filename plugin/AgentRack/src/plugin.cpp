#include <rack.hpp>

// Forward declarations -- one per module source file
extern rack::Model* modelAttenuate;
extern rack::Model* modelADSR;
extern rack::Model* modelCrinkle;
extern rack::Model* modelInspector;
extern rack::Model* modelLadder;
extern rack::Model* modelNoise;
extern rack::Model* modelSaphire;
extern rack::Model* modelSonic;

rack::Plugin* pluginInstance;

void init(rack::Plugin* p) {
    pluginInstance = p;
    p->addModel(modelAttenuate);
    p->addModel(modelADSR);
    p->addModel(modelCrinkle);
    p->addModel(modelInspector);
    p->addModel(modelLadder);
    p->addModel(modelNoise);
    p->addModel(modelSaphire);
    p->addModel(modelSonic);
}
