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
extern rack::Model* modelKck;
extern rack::Model* modelLowTom;
extern rack::Model* modelMidTom;
extern rack::Model* modelHighTom;
extern rack::Model* modelChh;
extern rack::Model* modelOhh;
extern rack::Model* modelRimClap;
extern rack::Model* modelSnr;
extern rack::Model* modelTomDbg;
extern rack::Model* modelToms;
extern rack::Model* modelKckDbg;
extern rack::Model* modelCrashRide;
extern rack::Model* modelTr909Ctrl;

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
    p->addModel(modelKck);
    p->addModel(modelLowTom);
    p->addModel(modelMidTom);
    p->addModel(modelHighTom);
    p->addModel(modelChh);
    p->addModel(modelOhh);
    p->addModel(modelRimClap);
    p->addModel(modelSnr);
    p->addModel(modelTomDbg);
    p->addModel(modelToms);
    p->addModel(modelKckDbg);
    p->addModel(modelCrashRide);
    p->addModel(modelTr909Ctrl);
}
