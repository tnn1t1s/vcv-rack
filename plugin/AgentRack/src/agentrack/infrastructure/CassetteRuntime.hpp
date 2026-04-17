#pragma once

#include "../../tape/LoopPack.hpp"
#include <atomic>
#include <memory>

namespace AgentRack {
namespace Infrastructure {

class CassetteRuntime {
public:
    CassetteRuntime() : activePack_(&getInternalPack()) {
    }

    ~CassetteRuntime() {
        delete pendingPack_.exchange(nullptr);
    }

    LoopPack* activePack() const {
        return activePack_;
    }

    int currentLoop() const {
        return currentLoop_;
    }

    bool isPlaying() const {
        return playing_;
    }

    bool isSwapping() const {
        return swapping_;
    }

    const std::string& activePackPath() const {
        return activePack_->indexPath;
    }

    void setPlaying(bool playing) {
        playing_ = playing;
    }

    void togglePlaying() {
        playing_ = !playing_;
    }

    void postLoadedPack(LoopPack* pack) {
        delete pendingPack_.exchange(pack);
    }

    bool loadPackFromPath(const std::string& path) {
        LoopPack* newPack = new LoopPack();
        if (!loadPackFromDisk(path, *newPack)) {
            delete newPack;
            return false;
        }
        postLoadedPack(newPack);
        return true;
    }

    template <typename Engine>
    void consumePendingPack(Engine& engine) {
        LoopPack* pending = pendingPack_.exchange(nullptr);
        if (!pending) {
            return;
        }

        ownedPack_.reset(pending);
        activePack_ = ownedPack_.get();
        currentLoop_ = 0;
        pendingLoop_ = -1;
        swapping_ = false;
        engine.reset();
    }

    void requestLoop(int targetLoop) {
        if (targetLoop == currentLoop_) {
            return;
        }
        pendingLoop_ = targetLoop;
        if (!swapping_) {
            swapping_ = true;
        }
    }

    bool engineShouldPlay() const {
        return swapping_ ? false : playing_;
    }

    template <typename Engine>
    void completeSwapIfReady(Engine& engine) {
        if (!swapping_ || engine.speedRamp >= 0.01f) {
            return;
        }
        currentLoop_ = pendingLoop_;
        pendingLoop_ = -1;
        swapping_ = false;
        engine.reset();
    }

    template <typename Engine>
    void resetToInternal(Engine& engine) {
        delete pendingPack_.exchange(nullptr);
        ownedPack_.reset();
        activePack_ = &getInternalPack();
        currentLoop_ = 0;
        pendingLoop_ = -1;
        swapping_ = false;
        engine.reset();
    }

private:
    std::unique_ptr<LoopPack> ownedPack_;
    LoopPack* activePack_ = nullptr;
    std::atomic<LoopPack*> pendingPack_{nullptr};

    int currentLoop_ = 0;
    int pendingLoop_ = -1;
    bool swapping_ = false;
    bool playing_ = true;
};

} // namespace Infrastructure
} // namespace AgentRack
