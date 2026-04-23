#!/bin/bash
#
# BBR vs CUBIC Automated Experiment Script
# Replicating Figures 5(a) and 5(b) from Cao et al., IMC 2019
#

# --- Parameters ---
RTTS=(10 50 100 200)
BWS=(10 100 500 1000)
BUFFERS=(100000 10000000)
ALGOS=("bbr" "cubic")
REPS=3
DURATION=60
OUTDIR="$HOME/bbr-experiment/results"
CSVFILE="$OUTDIR/all_results.csv"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$OUTDIR"

# CSV header
echo "algo,rtt_ms,bw_mbps,buffer_bytes,rep,goodput_mbps,retransmits" > "$CSVFILE"

# Load BBR module
sudo modprobe tcp_bbr

# Count total runs
TOTAL=$(( ${#ALGOS[@]} * ${#RTTS[@]} * ${#BWS[@]} * ${#BUFFERS[@]} * REPS ))
COUNT=0

echo "Starting BBR vs CUBIC experiments..."
echo "Total runs: $TOTAL"
echo "Estimated time: $(( TOTAL * (DURATION + 15) / 60 )) minutes"
echo ""

START_TIME=$(date +%s)

for algo in "${ALGOS[@]}"; do
    for buf in "${BUFFERS[@]}"; do
        for rtt in "${RTTS[@]}"; do
            for bw in "${BWS[@]}"; do
                for rep in $(seq 1 $REPS); do
                    COUNT=$((COUNT + 1))
                    echo "============================================"
                    echo "  [$COUNT/$TOTAL] Algo: $algo | RTT: ${rtt}ms | BW: ${bw}Mbps | Buffer: $buf | Rep: $rep"
                    echo "============================================"

                    # Cleanup any leftover Mininet state
                    sudo mn -c > /dev/null 2>&1
                    sleep 2

                    # Run the experiment
                    sudo python3 "$SCRIPT_DIR/run_one.py" "$algo" "$rtt" "$bw" "$buf" "$rep" "$DURATION" "$CSVFILE"

                    sleep 3
                done
            done
        done
    done
done

END_TIME=$(date +%s)
ELAPSED=$(( END_TIME - START_TIME ))

echo ""
echo "============================================"
echo "  ALL EXPERIMENTS COMPLETE"
echo "  Total time: $(( ELAPSED / 3600 ))h $(( (ELAPSED % 3600) / 60 ))m $(( ELAPSED % 60 ))s"
echo "  Results saved to: $CSVFILE"
echo "============================================"