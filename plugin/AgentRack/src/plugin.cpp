#include <rack.hpp>

// Forward declarations -- one per module source file
extern rack::Model* modelAttenuate;
extern rack::Model* modelADSR;
extern rack::Model* modelCassette;
extern rack::Model* modelCrinkle;
extern rack::Model* modelLadder;
extern rack::Model* modelNoise;
extern rack::Model* modelSaphire;
extern rack::Model* modelSonic;
extern rack::Model* modelSteel;
extern rack::Model* modelBusCrush;
extern rack::Model* modelClockDiv;
extern rack::Model* modelTonnetz;
extern rack::Model* modelMaurizio;

rack::Plugin* pluginInstance;

void init(rack::Plugin* p) {
    pluginInstance = p;
    p->addModel(modelAttenuate);
    p->addModel(modelADSR);
    p->addModel(modelCassette);
    p->addModel(modelCrinkle);
    p->addModel(modelLadder);
    p->addModel(modelNoise);
    p->addModel(modelSaphire);
    p->addModel(modelSonic);
    p->addModel(modelSteel);
    p->addModel(modelBusCrush);
    p->addModel(modelClockDiv);
    p->addModel(modelTonnetz);
    p->addModel(modelMaurizio);
}
