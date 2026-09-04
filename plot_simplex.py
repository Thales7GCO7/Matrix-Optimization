import matplotlib.pyplot as plt
import numpy as np

x1 = np.linspace(0, 10, 400)

# Restrições: A * x <= b
# x1 <= 4
# 2x2 <= 12  →  x2 <= 6
# 3x1 + 2x2 <= 18  →  x2 <= (18 - 3x1) / 2

x2_1 = np.full_like(x1, 6)       # x2 <= 6
x2_2 = (18 - 3 * x1) / 2         # x2 <= (18 - 3x1)/2

fig, ax = plt.subplots(figsize=(8, 6))

# Preenche a região viável
x2_min = np.zeros_like(x1)
x2_max = np.minimum(x2_1, x2_2)
x2_max = np.maximum(x2_max, 0)

# Máscara: x1 entre 0 e 4, e x2 entre 0 e x2_max
mask = (x1 >= 0) & (x1 <= 4)
ax.fill_between(x1[mask], 0, x2_max[mask], alpha=0.3, color='green', label='Região viável')

# Plota as restrições
ax.plot(x1, x2_1, 'b-', linewidth=2, label='x₂ <= 6')
ax.plot(x1[x1 <= 6], (18 - 3 * x1[x1 <= 6]) / 2, 'r-', linewidth=2, label='3x₁ + 2x₂ <= 18')
ax.axvline(x=4, color='purple', linestyle='--', linewidth=2, label='x₁ <= 4')

# Plota as linhas de nível de z = 3x₁ + 5x₂
for z_val in [10, 20, 30, 42]:
    x2_z = (z_val - 3 * x1) / 5
    ax.plot(x1, x2_z, 'k--', alpha=0.3, linewidth=1)
    ax.text(0.5, (z_val - 3 * 0.5) / 5 + 0.3, f'z={z_val}', fontsize=8, color='gray')

# Ponto ótimo: x1=4, x2=3 → z=42
# Verifica: 3(4) + 2(3) = 18 <= 18 ✓
ax.plot(4, 3, 'r*', markersize=15, label='Ótimo (4, 3) → z=42')

# Vértices da região viável
vertices = [(0, 0), (4, 0), (4, 3), (2, 6), (0, 6)]
for v in vertices:
    ax.plot(v[0], v[1], 'ko', markersize=5)
    ax.annotate(f'({v[0]},{v[1]})', (v[0], v[1]), textcoords="offset points",
                xytext=(8, 8), fontsize=9)

ax.set_xlim(-0.5, 8)
ax.set_ylim(-0.5, 8)
ax.set_xlabel('x₁')
ax.set_ylabel('x₂')
ax.set_title('Simplex: Região Viável e Função Objetivo\nmax z = 3x₁ + 5x₂')
ax.legend(loc='upper right')
ax.grid(True, alpha=0.3)
ax.set_aspect('equal')

plt.tight_layout()
plt.savefig('simplex_plot.png', dpi=150)
print("Grafico salvo em simplex_plot.png")
