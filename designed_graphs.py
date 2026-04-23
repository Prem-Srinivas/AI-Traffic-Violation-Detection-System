import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patheffects as path_effects

# Configuration for Premium Aesthetics
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['text.color'] = '#e2e8f0'
plt.rcParams['axes.facecolor'] = '#0f172a'
plt.rcParams['figure.facecolor'] = '#0f172a'
plt.rcParams['axes.edgecolor'] = '#1e293b'
plt.rcParams['axes.labelcolor'] = '#94a3b8'
plt.rcParams['xtick.color'] = '#64748b'
plt.rcParams['ytick.color'] = '#64748b'
plt.rcParams['grid.color'] = '#1e293b'
plt.rcParams['grid.alpha'] = 0.5
plt.rcParams['legend.facecolor'] = '#1e293b'
plt.rcParams['legend.edgecolor'] = '#334155'

# Data
categories = ['Helmet', 'Triple Riding', 'Speeding', 'License Plate']
precision = [93.1, 91.2, 88.9, 96.5]
recall = [91.4, 89.6, 87.2, 94.8]
map_scores = [92.0, 90.3, 89.1, 95.6]

models = ['Faster R-CNN', 'SSD', 'YOLOv3', 'Proposed System']
model_map = [85.0, 83.6, 87.2, 91.8]

violations = ['Helmet', 'Triple Riding', 'Speeding', 'Normal Traffic']
counts = [12000, 6000, 7500, 50000]

# Training Data
training_models = ['Faster R-CNN', 'SSD', 'YOLOv5', 'YOLOv8', 'Proposed (YOLOv10/S.I.N)']
training_times = [12, 8.5, 6, 4.5, 3.2] # Hours
training_map = [85.0, 83.6, 88.5, 90.2, 91.8] # mAP

colors = ['#00f2ff', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444']

# --- Graph 1: Performance Metrics Comparison ---
def plot_performance_metrics():
    x = np.arange(len(categories))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 6.5))
    
    # Adding a subtle glow effect to bars
    rects1 = ax.bar(x - width, precision, width, label='Precision', color=colors[0], alpha=0.8, edgecolor=colors[0], linewidth=1)
    rects2 = ax.bar(x, recall, width, label='Recall', color=colors[1], alpha=0.8, edgecolor=colors[1], linewidth=1)
    rects3 = ax.bar(x + width, map_scores, width, label='mAP', color=colors[2], alpha=0.8, edgecolor=colors[2], linewidth=1)

    ax.set_ylabel('Percentage (%)', fontweight='bold', labelpad=10)
    ax.set_title('Detection Engine Performance Metrics', fontsize=16, fontweight='bold', color='#f8fafc', pad=25)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontweight='bold')
    ax.legend(frameon=True, borderpad=1, labelspacing=1)
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    ax.set_ylim(80, 100)
    
    # Add values on top
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height}%',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 5), textcoords="offset points",
                        ha='center', va='bottom', fontsize=9, fontweight='bold', color='#94a3b8')

    autolabel(rects1)
    autolabel(rects2)
    autolabel(rects3)

    plt.tight_layout()
    plt.savefig('performance_metrics.png', dpi=300)
    print("Saved performance_metrics.png")

# --- Graph 2: Model Comparison ---
def plot_model_comparison():
    plt.figure(figsize=(9, 6))
    ax = plt.gca()
    
    bars = plt.bar(models, model_map, color=colors[1], alpha=0.3, edgecolor=colors[1], linewidth=2)
    
    # Highlight the Proposed System
    bars[-1].set_alpha(0.8)
    bars[-1].set_color(colors[0])
    bars[-1].set_edgecolor(colors[0])
    
    plt.ylabel('mAP (%)', fontweight='bold')
    plt.title('Benchmark: Object Detection Models', fontsize=16, fontweight='bold', color='#f8fafc', pad=20)
    plt.grid(axis='y', alpha=0.1)
    plt.ylim(80, 95)
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 0.5, f'{yval}%', ha='center', va='bottom', fontweight='bold', color=colors[0] if bar == bars[-1] else '#94a3b8')

    plt.tight_layout()
    plt.savefig('model_comparison.png', dpi=300)
    print("Saved model_comparison.png")

# --- Graph 3: FPS and SMS Response Time ---
def plot_speed_metrics():
    metrics = ['Processing Speed (FPS)', 'SMS Alert Latency (Sec)']
    values = [25, 2]
    
    fig, ax1 = plt.subplots(figsize=(8, 5))
    
    # We use two separate types of display or a clean split
    color_fps = colors[0]
    color_sms = colors[4]
    
    ax1.bar(metrics[0], values[0], color=color_fps, alpha=0.7, width=0.5, edgecolor=color_fps, linewidth=2)
    ax1.set_ylabel('Frames Per Second', color=color_fps, fontweight='bold')
    ax1.tick_params(axis='y', labelcolor=color_fps)
    
    ax2 = ax1.twinx()
    ax2.bar(metrics[1], values[1], color=color_sms, alpha=0.7, width=0.5, edgecolor=color_sms, linewidth=2)
    ax2.set_ylabel('Latency (Seconds)', color=color_sms, fontweight='bold')
    ax2.tick_params(axis='y', labelcolor=color_sms)
    
    plt.title('System Throughput & Response Time', fontsize=16, fontweight='bold', color='#f8fafc', pad=20)
    plt.tight_layout()
    plt.savefig('system_speed.png', dpi=300)
    print("Saved system_speed.png")

# --- Graph 4: Violation Distribution Donut Chart ---
def plot_distribution_donut():
    plt.figure(figsize=(8, 8))
    
    # Donut instead of pie for more modern look
    wedgeprops = {'width': 0.4, 'edgecolor': '#0f172a', 'linewidth': 5}
    
    plt.pie(counts, labels=violations, autopct='%1.1f%%', 
            colors=[colors[4], colors[1], colors[3], '#334155'], 
            pctdistance=0.85, textprops={'color': "#f8fafc", 'fontweight': 'bold'},
            wedgeprops=wedgeprops, startangle=140)
    
    # Add center text
    plt.text(0, 0, 'Total Units\n' + str(sum(counts)), ha='center', va='center', fontsize=14, fontweight='bold', color='#94a3b8')
    
    plt.title('Traffic Composition & Violation Spread', fontsize=16, fontweight='bold', color='#f8fafc', pad=20)
    plt.tight_layout()
    plt.savefig('violation_distribution.png', dpi=300)
    print("Saved violation_distribution.png")

# --- Graph 5: Day vs Night Accuracy ---
def plot_environmental_accuracy():
    conditions = ['Daylight Ops', 'Low-Light Ops']
    accuracy = [95, 87]
    
    plt.figure(figsize=(7, 5))
    bars = plt.bar(conditions, accuracy, color=[colors[0], colors[2]], alpha=0.6, width=0.6, edgecolor='white', linewidth=1)
    
    plt.ylabel('Accuracy (%)', fontweight='bold')
    plt.title('Environmental Reliability Analysis', fontsize=16, fontweight='bold', color='#f8fafc', pad=20)
    plt.ylim(0, 110)
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 2, f'{yval}%', ha='center', va='bottom', fontweight='bold')

    plt.grid(axis='y', alpha=0.05)
    plt.tight_layout()
    plt.savefig('day_night_accuracy.png', dpi=300)
    print("Saved day_night_accuracy.png")

# --- Graph 6: Training Time vs Performance ---
def plot_training_time_performance():
    plt.figure(figsize=(10, 6))
    ax = plt.gca()
    
    # Scatter plot with size based on performance efficiency
    sizes = [ (m/t) * 10 for m, t in zip(training_map, training_times)]
    
    # Plot connections to show the "Pareto Frontier" or improvement path
    plt.plot(training_times, training_map, color='#334155', linestyle='--', alpha=0.5, zorder=1)
    
    for i, model in enumerate(training_models):
        color = colors[0] if 'Proposed' in model else colors[1]
        alpha = 0.9 if 'Proposed' in model else 0.5
        
        # Draw the point
        plt.scatter(training_times[i], training_map[i], s=500, color=color, alpha=alpha, edgecolors='white', linewidth=2, zorder=2, label=model if i == 0 or 'Proposed' in model else "")
        
        # Add Label
        plt.text(training_times[i], training_map[i] - 0.8, model, ha='center', va='top', fontweight='bold', fontsize=9, color='#e2e8f0')
    
    plt.xlabel('Training Time (Hours) - Lower is Better', fontweight='bold')
    plt.ylabel('Performance (mAP %) - Higher is Better', fontweight='bold')
    plt.title('Training Efficiency vs. Detection Accuracy', fontsize=16, fontweight='bold', color='#f8fafc', pad=25)
    
    plt.grid(True, linestyle=':', alpha=0.2)
    plt.xlim(max(training_times) + 1, min(training_times) - 1) # Invert X-axis because lower is better
    plt.ylim(80, 95)
    
    plt.tight_layout()
    plt.savefig('training_comparison.png', dpi=300)
    print("Saved training_comparison.png")

# Run all
if __name__ == "__main__":
    plot_performance_metrics()
    plot_model_comparison()
    plot_speed_metrics()
    plot_distribution_donut()
    plot_environmental_accuracy()
    plot_training_time_performance()
