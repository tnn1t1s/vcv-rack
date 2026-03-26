#pragma once
#include <rack.hpp>
#include <string>

/**
 * AgentModule -- base class for all AgentRack modules.
 *
 * Every AgentRack module embeds a manifest string that describes its
 * semantic interface (port types, roles, param units, behavioral
 * guarantees) in a form an agent can read without source inspection.
 *
 * The manifest is pure data: no rack_id, no plugin name, no runtime
 * knowledge. A separate projection file maps semantic names to Rack IDs.
 */
struct AgentModule : rack::Module {
    /**
     * Return the module's semantic manifest as a JSON string.
     * The manifest describes ports (signal_class, semantic_role),
     * params (unit, scale, min, max, default), and behavioral guarantees.
     * It does NOT contain rack_id or any runtime-specific information.
     */
    virtual std::string getManifest() const = 0;

    /**
     * Called by an Inspector module (or external tooling) to retrieve
     * the manifest as a Jansson JSON object. Caller owns the result.
     */
    json_t* getAgentJson() const {
        json_error_t err;
        json_t* j = json_loads(getManifest().c_str(), 0, &err);
        if (!j) {
            WARN("AgentModule: failed to parse manifest JSON: %s", err.text);
        }
        return j;
    }
};
