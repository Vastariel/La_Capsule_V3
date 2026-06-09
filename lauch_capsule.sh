#!/usr/bin/env bash
#
# Lanceur La Capsule V3.
#   1. Démarre le bridge Python (main.py)
#   2. Attend 5 secondes
#   3. Lance l'application Godot (capsule.arm4)
#
# Quand l'un des deux processus s'arrête (ou sur Ctrl-C), l'autre est arrêté
# proprement pour ne pas laisser de processus orphelin.

set -u

BRIDGE="/home/capsule/Desktop/La_Capsule_V3/bridge_python/main.py"
GODOT_APP="/home/capsule/Desktop/La_Capsule_V3/capsule.arm64"
WORKDIR="$(dirname "$BRIDGE")"

# Écran : rotation attendue (90° horaire = transform 270) sur la sortie HDMI.
SCREEN_OUTPUT="HDMI-A-1"
SCREEN_TRANSFORM="270"

BRIDGE_PID=""
GODOT_PID=""

cleanup() {
    echo
    echo "[LAUNCH] Arrêt..."
    [ -n "$GODOT_PID" ]  && kill "$GODOT_PID"  2>/dev/null
    [ -n "$BRIDGE_PID" ] && kill "$BRIDGE_PID" 2>/dev/null
    wait 2>/dev/null
    echo "[LAUNCH] Terminé."
}
trap cleanup EXIT INT TERM

# ---- 0. Test : écran tourné -----------------------------------------------
# Vérifie que l'écran est bien en rotation 270 (90° horaire). Si ce n'est pas
# le cas (script lancé hors session graphique configurée), tente de l'appliquer.
read_transform() {
    wlr-randr 2>/dev/null | awk -v o="$SCREEN_OUTPUT" '
        $1==o {found=1}
        found && /Transform:/ {print $2; exit}'
}

check_screen_rotation() {
    export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
    if [ -z "${WAYLAND_DISPLAY:-}" ]; then
        WAYLAND_DISPLAY="$(basename "$(ls "$XDG_RUNTIME_DIR"/wayland-* 2>/dev/null | grep -v '\.lock' | head -n1)")"
        export WAYLAND_DISPLAY
    fi

    if ! command -v wlr-randr >/dev/null 2>&1; then
        echo "[TEST] ⚠ wlr-randr absent : rotation non vérifiée." >&2
        return 0
    fi

    local current
    current="$(read_transform)"
    if [ "$current" = "$SCREEN_TRANSFORM" ]; then
        echo "[TEST] ✓ Écran $SCREEN_OUTPUT tourné (transform $current)."
        return 0
    fi

    echo "[TEST] Écran non tourné (transform actuel: ${current:-inconnu}) — application..."
    wlr-randr --output "$SCREEN_OUTPUT" --transform "$SCREEN_TRANSFORM" 2>/dev/null
    sleep 1
    current="$(read_transform)"
    if [ "$current" = "$SCREEN_TRANSFORM" ]; then
        echo "[TEST] ✓ Rotation appliquée (transform $current)."
        return 0
    fi

    echo "[TEST] ⚠ Impossible de confirmer la rotation (transform: ${current:-inconnu}). On continue." >&2
    return 0
}

check_screen_rotation

# ---- 1. Bridge Python -----------------------------------------------------
if [ ! -f "$BRIDGE" ]; then
    echo "✗ Introuvable : $BRIDGE" >&2
    exit 1
fi

echo "[LAUNCH] Démarrage du bridge Python..."
cd "$WORKDIR" || exit 1
python3 "$BRIDGE" &
BRIDGE_PID=$!

# ---- 2. Attente -----------------------------------------------------------
echo "[LAUNCH] Attente de 5 secondes..."
sleep 5

# Le bridge a-t-il survécu au démarrage ?
if ! kill -0 "$BRIDGE_PID" 2>/dev/null; then
    echo "✗ Le bridge Python s'est arrêté pendant le démarrage." >&2
    exit 1
fi

# ---- 3. Application Godot --------------------------------------------------
if [ ! -x "$GODOT_APP" ]; then
    echo "✗ Introuvable ou non exécutable : $GODOT_APP" >&2
    echo "  (rends-le exécutable avec : chmod +x \"$GODOT_APP\")" >&2
    exit 1
fi

echo "[LAUNCH] Démarrage de l'application Godot..."
"$GODOT_APP" &
GODOT_PID=$!

# ---- Surveillance : on s'arrête dès qu'un des deux se termine --------------
wait -n "$BRIDGE_PID" "$GODOT_PID"
