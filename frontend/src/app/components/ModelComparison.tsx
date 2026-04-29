import { useEffect, useState, useRef } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { uploadDataset } from '../../api/threatApi';

interface ModelMetrics {
  accuracy: number;
  confusion_matrix: number[][];
}

interface MetricsResponse {
  classes: string[];
  random_forest: ModelMetrics;
  logistic_regression: ModelMetrics;
  attack_classifier?: {
    accuracy: number;
    confusion_matrix: number[][];
    classes: string[];
  };
}

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

function ConfusionMatrix({ matrix, classes, color }: {
  matrix: number[][];
  classes: string[];
  color: string;
}) {
  if (!matrix || matrix.length === 0) return null;

  // Find max for color intensity
  const flat = matrix.flat();
  const max  = Math.max(...flat);

  const colorMap: Record<string, string> = {
    cyan:   'rgba(6,182,212,',
    purple: 'rgba(168,85,247,',
  };
  const base = colorMap[color] || colorMap.cyan;

  return (
    <div className="w-full">
      {/* Header row */}
      <div className="flex mb-1">
        <div className="w-14 shrink-0" />
        {classes.map((c: string) => (
          <div key={c} className="flex-1 text-center text-xs font-mono text-gray-400 truncate">
            {c}
          </div>
        ))}
      </div>

      {matrix.map((row: number[], i: number) => (
        <div key={i} className="flex mb-1 items-center">
          {/* Row label */}
          <div className="w-14 shrink-0 text-xs font-mono text-gray-400 text-right pr-2 truncate">
            {classes[i]}
          </div>
          {row.map((val: number, j: number) => {
            const intensity = max > 0 ? val / max : 0;
            const isCorrect = i === j;
            return (
              <div
                key={j}
                className="flex-1 aspect-square flex items-center justify-center text-xs font-mono font-bold rounded mx-0.5 transition-all duration-500"
                style={{
                  background: `${base}${(intensity * 0.8 + 0.1).toFixed(2)})`,
                  border: isCorrect ? `1px solid ${base}0.9)` : '1px solid transparent',
                  color: intensity > 0.5 ? '#fff' : '#aaa',
                  minHeight: 36,
                }}
                title={`Actual: ${classes[i]}, Predicted: ${classes[j]}: ${val}`}
              >
                {val.toLocaleString()}
              </div>
            );
          })}
        </div>
      ))}

      {/* Predicted label */}
      <div className="flex mt-1">
        <div className="w-14 shrink-0" />
        <div className="flex-1 text-center text-xs text-gray-500 font-mono">← PREDICTED →</div>
      </div>
    </div>
  );
}

export function ModelComparison() {
  const [data,    setData]    = useState<MetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);
  const [active,  setActive]  = useState<'both' | 'rf' | 'lr'>('both');
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchMetrics = () => {
    setLoading(true);
    setError(null);
    fetch(`${BASE_URL}/model-metrics`)
      .then(r => r.json())
      .then(d => {
        if (d.error) {
          setError(d.error);
        } else {
          setData(d);
        }
        setLoading(false);
      })
      .catch(e => { setError(e.message); setLoading(false); });
  };

  useEffect(() => { fetchMetrics(); }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadMsg(null);
    try {
      const result = await uploadDataset(file);
      setUploadMsg(result.message || 'Upload successful!');
      // Refetch metrics after upload
      setTimeout(() => fetchMetrics(), 500);
    } catch (err: any) {
      setUploadMsg(`Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const barData = data ? [
    { name: 'Random Forest',       accuracy: data.random_forest.accuracy,       fill: '#06b6d4' },
    { name: 'Logistic Regression', accuracy: data.logistic_regression.accuracy, fill: '#a855f7' },
  ] : [];

  const showRF = active === 'both' || active === 'rf';
  const showLR = active === 'both' || active === 'lr';

  return (
    <div className="mt-6 bg-black/50 border border-cyan-500/30 rounded-lg p-5">
      {/* Section header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-5">
        <h2 className="text-cyan-400 text-xs font-mono tracking-widest">
          ◈ MODEL PERFORMANCE ANALYTICS
        </h2>
        {/* Toggle buttons */}
        <div className="flex gap-2 text-xs font-mono">
          {(['both', 'rf', 'lr'] as const).map(v => (
            <button
              key={v}
              onClick={() => setActive(v)}
              className={`px-3 py-1 rounded border transition-all ${
                active === v
                  ? 'bg-cyan-500/20 border-cyan-500 text-cyan-300'
                  : 'border-gray-700 text-gray-500 hover:border-cyan-500/50'
              }`}
            >
              {v === 'both' ? 'BOTH' : v === 'rf' ? 'RANDOM FOREST' : 'LOGISTIC REG'}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="text-center py-12 text-cyan-400 font-mono text-sm animate-pulse">
          ⟳ LOADING MODEL METRICS... (training both models on dataset)
        </div>
      )}

      {error && (
        <div className="space-y-3">
          <div className="text-red-400 font-mono text-xs p-3 border border-red-500/30 rounded bg-red-900/20">
            ⚠ {error} — Make sure the backend server (backend_final.py) is running on port 5000
          </div>
          {/* File upload fallback */}
          <div className="p-4 border border-cyan-500/30 rounded bg-cyan-900/10">
            <div className="text-cyan-400 font-mono text-xs mb-2 tracking-wider">
              📂 UPLOAD DATASET MANUALLY
            </div>
            <p className="text-gray-400 text-xs font-mono mb-3">
              If KDDTrain+.txt is missing from the backend folder, upload it here to retrain the models:
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.csv"
              onChange={handleUpload}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="px-4 py-2 bg-cyan-600/30 border border-cyan-500 text-cyan-300 rounded font-mono text-xs tracking-wider hover:bg-cyan-600/50 transition-all disabled:opacity-50"
            >
              {uploading ? '⟳ UPLOADING & TRAINING...' : '⬆ SELECT KDDTrain+.txt'}
            </button>
            {uploadMsg && (
              <div className={`mt-2 text-xs font-mono ${uploadMsg.includes('failed') ? 'text-red-400' : 'text-green-400'}`}>
                {uploadMsg}
              </div>
            )}
          </div>
        </div>
      )}

      {data && !loading && (
        <>
          {/* Accuracy comparison bar chart */}
          <div className="mb-6">
            <h3 className="text-gray-400 text-xs font-mono mb-3 tracking-wider">ACCURACY COMPARISON</h3>
            <div className="grid grid-cols-2 gap-4 mb-4">
              {showRF && (
                <div className="bg-cyan-500/10 border border-cyan-500/30 rounded p-3 text-center">
                  <div className="text-2xl font-bold text-cyan-400 font-mono">
                    {data.random_forest.accuracy}%
                  </div>
                  <div className="text-xs text-gray-400 mt-1 font-mono tracking-wider">RANDOM FOREST</div>
                  <div className="mt-2 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                    <div className="h-full bg-cyan-500 rounded-full transition-all duration-1000"
                      style={{ width: `${data.random_forest.accuracy}%` }} />
                  </div>
                </div>
              )}
              {showLR && (
                <div className="bg-purple-500/10 border border-purple-500/30 rounded p-3 text-center">
                  <div className="text-2xl font-bold text-purple-400 font-mono">
                    {data.logistic_regression.accuracy}%
                  </div>
                  <div className="text-xs text-gray-400 mt-1 font-mono tracking-wider">LOGISTIC REGRESSION</div>
                  <div className="mt-2 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                    <div className="h-full bg-purple-500 rounded-full transition-all duration-1000"
                      style={{ width: `${data.logistic_regression.accuracy}%` }} />
                  </div>
                </div>
              )}
            </div>

            <ResponsiveContainer width="100%" height={120}>
              <BarChart data={barData.filter(d =>
                (d.name === 'Random Forest' && showRF) ||
                (d.name === 'Logistic Regression' && showLR)
              )} barSize={50}>
                <XAxis dataKey="name" stroke="#06b6d4" fontSize={10} />
                <YAxis domain={[80, 100]} stroke="#06b6d4" fontSize={10} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#000', border: '1px solid #06b6d4', fontSize: 11 }}
                  formatter={(v: number) => [`${v}%`, 'Accuracy']}
                />
                <Bar dataKey="accuracy" radius={[4, 4, 0, 0]}>
                  {barData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Attack classifier accuracy */}
          {data.attack_classifier && (
            <div className="mb-6 p-3 bg-green-500/10 border border-green-500/30 rounded">
              <div className="flex items-center justify-between">
                <span className="text-green-400 font-mono text-xs tracking-wider">
                  ✓ 5-CLASS ATTACK CLASSIFIER (Normal / DoS / Probe / R2L / U2R)
                </span>
                <span className="text-green-300 text-sm font-mono font-bold bg-green-500/20 px-2 py-0.5 rounded">
                  {data.attack_classifier.accuracy}%
                </span>
              </div>
            </div>
          )}

          {/* Confusion matrices */}
          <div className={`grid gap-6 ${active === 'both' ? 'grid-cols-1 lg:grid-cols-2' : 'grid-cols-1'}`}>
            {showRF && (
              <div className="bg-black/40 border border-cyan-500/20 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-cyan-400 text-xs font-mono tracking-wider">
                    RANDOM FOREST — CONFUSION MATRIX
                  </h3>
                  <span className="text-cyan-300 text-xs font-mono bg-cyan-500/10 px-2 py-0.5 rounded">
                    {data.random_forest.accuracy}%
                  </span>
                </div>
                <ConfusionMatrix
                  matrix={data.random_forest.confusion_matrix}
                  classes={data.classes}
                  color="cyan"
                />
              </div>
            )}

            {showLR && (
              <div className="bg-black/40 border border-purple-500/20 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-purple-400 text-xs font-mono tracking-wider">
                    LOGISTIC REGRESSION — CONFUSION MATRIX
                  </h3>
                  <span className="text-purple-300 text-xs font-mono bg-purple-500/10 px-2 py-0.5 rounded">
                    {data.logistic_regression.accuracy}%
                  </span>
                </div>
                <ConfusionMatrix
                  matrix={data.logistic_regression.confusion_matrix}
                  classes={data.classes}
                  color="purple"
                />
              </div>
            )}
          </div>

          {/* Winner banner */}
          {active === 'both' && (
            <div className="mt-4 p-3 bg-green-500/10 border border-green-500/30 rounded text-center">
              <span className="text-green-400 font-mono text-xs tracking-wider">
                ✓ WINNER: {
                  data.random_forest.accuracy >= data.logistic_regression.accuracy
                    ? `RANDOM FOREST (+${(data.random_forest.accuracy - data.logistic_regression.accuracy).toFixed(2)}% more accurate)`
                    : `LOGISTIC REGRESSION (+${(data.logistic_regression.accuracy - data.random_forest.accuracy).toFixed(2)}% more accurate)`
                }
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
}
