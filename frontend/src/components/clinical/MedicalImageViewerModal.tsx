import React, { useState, useRef, useEffect } from 'react';
import { ZoomIn, ZoomOut, RotateCw, RotateCcw, FlipHorizontal, FlipVertical, Sun, Contrast, Eye, EyeOff, Ruler, Maximize2, Minimize2, RotateCcw as ResetIcon, X, Download, Layers } from 'lucide-react';
import toast from 'react-hot-toast';

interface MedicalImageViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  imageUrl: string;
  title?: string;
  patientName?: string;
  date?: string;
}

type WindowingPreset = 'DEFAULT' | 'BONE' | 'SOFT_TISSUE' | 'LUNG';

export default function MedicalImageViewerModal({
  isOpen,
  onClose,
  imageUrl,
  title = 'صورة طبية / أشعة',
  patientName,
  date,
}: MedicalImageViewerModalProps) {
  // Transformation states
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [flipH, setFlipH] = useState(false);
  const [flipV, setFlipV] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Filter & Windowing states
  const [preset, setPreset] = useState<WindowingPreset>('DEFAULT');
  const [invert, setInvert] = useState(false);
  const [brightness, setBrightness] = useState(100);
  const [contrast, setContrast] = useState(100);

  // Measurement Caliper tool
  const [rulerActive, setRulerActive] = useState(false);
  const [rulerPoints, setRulerPoints] = useState<{ start: { x: number; y: number } | null; end: { x: number; y: number } | null }>({
    start: null,
    end: null,
  });

  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Reset view
  const handleReset = () => {
    setZoom(1);
    setRotation(0);
    setFlipH(false);
    setFlipV(false);
    setPosition({ x: 0, y: 0 });
    setPreset('DEFAULT');
    setInvert(false);
    setBrightness(100);
    setContrast(100);
    setRulerPoints({ start: null, end: null });
    setRulerActive(false);
  };

  useEffect(() => {
    if (isOpen) {
      handleReset();
    }
  }, [isOpen, imageUrl]);

  // Windowing presets logic
  const handlePresetChange = (newPreset: WindowingPreset) => {
    setPreset(newPreset);
    if (newPreset === 'BONE') {
      setBrightness(110);
      setContrast(180);
      setInvert(false);
    } else if (newPreset === 'SOFT_TISSUE') {
      setBrightness(105);
      setContrast(130);
      setInvert(false);
    } else if (newPreset === 'LUNG') {
      setBrightness(125);
      setContrast(160);
      setInvert(true);
    } else {
      setBrightness(100);
      setContrast(100);
      setInvert(false);
    }
  };

  // Mouse pan handling
  const handleMouseDown = (e: React.MouseEvent) => {
    if (rulerActive) {
      const rect = e.currentTarget.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      if (!rulerPoints.start || (rulerPoints.start && rulerPoints.end)) {
        setRulerPoints({ start: { x, y }, end: null });
      } else {
        setRulerPoints((prev) => ({ ...prev, end: { x, y } }));
      }
      return;
    }

    setIsDragging(true);
    setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (rulerActive && rulerPoints.start && !rulerPoints.end) {
      // preview ruler line
    }
    if (!isDragging || rulerActive) return;
    setPosition({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Wheel zoom
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY * -0.0015;
    setZoom((prev) => Math.min(Math.max(0.5, prev + delta), 4.5));
  };

  // Distance calculation
  const distancePx =
    rulerPoints.start && rulerPoints.end
      ? Math.sqrt(
          Math.pow(rulerPoints.end.x - rulerPoints.start.x, 2) +
            Math.pow(rulerPoints.end.y - rulerPoints.start.y, 2)
        )
      : null;

  // Approx mm conversion (standard 96dpi baseline)
  const distanceMm = distancePx ? (distancePx * 0.264583).toFixed(1) : null;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[120] bg-black/90 backdrop-blur-xl flex flex-col select-none animate-in fade-in duration-200">
      {/* Top Bar / Metadata */}
      <div className="h-14 px-6 border-b border-gray-800 bg-gray-950/80 flex items-center justify-between text-white" dir="rtl">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-teal-500/20 border border-teal-500/30 flex items-center justify-center text-teal-400">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>{title}</span>
              {patientName && (
                <span className="text-xs px-2 py-0.5 rounded bg-gray-800 text-teal-300 font-normal">
                  المريض: {patientName}
                </span>
              )}
            </h3>
            {date && <p className="text-[10px] text-gray-400">تاريخ الفحص: {date}</p>}
          </div>
        </div>

        {/* Viewport indicators */}
        <div className="hidden md:flex items-center gap-4 text-xs font-mono text-gray-400">
          <span>تكبير: {Math.round(zoom * 100)}%</span>
          <span>تدوير: {rotation}°</span>
          <span>سطوع: {brightness}%</span>
          <span>تباين: {contrast}%</span>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-2 hover:bg-gray-800 rounded-lg text-gray-400 hover:text-white transition-colors"
            title={isFullscreen ? 'تصغير' : 'ملء الشاشة'}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
          <button
            onClick={onClose}
            className="p-2 hover:bg-red-500/20 text-gray-400 hover:text-red-400 rounded-lg transition-colors"
            title="إغلاق"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Main Radiology Workspace */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Viewport Canvas Container */}
        <div
          ref={containerRef}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onWheel={handleWheel}
          className={`flex-1 bg-black flex items-center justify-center overflow-hidden relative ${
            rulerActive ? 'cursor-crosshair' : isDragging ? 'cursor-grabbing' : 'cursor-grab'
          }`}
        >
          {/* Diagnostic Image */}
          <img
            src={imageUrl}
            alt={title}
            draggable={false}
            style={{
              transform: `translate(${position.x}px, ${position.y}px) scale(${zoom}) rotate(${rotation}deg) scaleX(${flipH ? -1 : 1}) scaleY(${flipV ? -1 : 1})`,
              filter: `${invert ? 'invert(1) ' : ''}brightness(${brightness}%) contrast(${contrast}%)`,
              transition: isDragging ? 'none' : 'transform 0.1s ease-out, filter 0.15s ease',
              maxHeight: isFullscreen ? '95vh' : '78vh',
              maxWidth: '90vw',
            }}
            className="object-contain pointer-events-none select-none rounded shadow-2xl"
          />

          {/* SVG Caliper / Ruler Overlay */}
          {rulerPoints.start && rulerPoints.end && (
            <svg className="absolute inset-0 w-full h-full pointer-events-none z-10">
              <line
                x1={rulerPoints.start.x}
                y1={rulerPoints.start.y}
                x2={rulerPoints.end.x}
                y2={rulerPoints.end.y}
                stroke="#14b8a6"
                strokeWidth="2.5"
                strokeDasharray="4 2"
              />
              <circle cx={rulerPoints.start.x} cy={rulerPoints.start.y} r="5" fill="#14b8a6" />
              <circle cx={rulerPoints.end.x} cy={rulerPoints.end.y} r="5" fill="#14b8a6" />
              <rect
                x={(rulerPoints.start.x + rulerPoints.end.x) / 2 - 35}
                y={(rulerPoints.start.y + rulerPoints.end.y) / 2 - 15}
                width="70"
                height="22"
                rx="6"
                fill="rgba(15, 23, 42, 0.85)"
                stroke="#14b8a6"
                strokeWidth="1"
              />
              <text
                x={(rulerPoints.start.x + rulerPoints.end.x) / 2}
                y={(rulerPoints.start.y + rulerPoints.end.y) / 2}
                fill="#ffffff"
                fontSize="11"
                fontFamily="monospace"
                fontWeight="bold"
                textAnchor="middle"
                dominantBaseline="middle"
              >
                {distanceMm} mm
              </text>
            </svg>
          )}

          {/* Measurement Floating Pill */}
          {rulerActive && (
            <div className="absolute top-4 left-4 bg-gray-900/90 border border-teal-500/40 text-white text-xs px-3.5 py-2 rounded-xl shadow-xl flex items-center gap-2" dir="rtl">
              <Ruler className="w-4 h-4 text-teal-400" />
              <span>
                {rulerPoints.start && !rulerPoints.end
                  ? 'انقر على النقطة الثانية لإنهاء القياس'
                  : rulerPoints.start && rulerPoints.end
                  ? `المسافة المقاسة: ${distanceMm} ملم (${Math.round(distancePx || 0)} px)`
                  : 'انقر على نقطتين لقياس المسافة السريرية (العظام/الورم)'}
              </span>
              {rulerPoints.start && (
                <button
                  onClick={() => setRulerPoints({ start: null, end: null })}
                  className="mr-2 text-teal-400 hover:text-teal-300 underline"
                >
                  إعادة ضبط
                </button>
              )}
            </div>
          )}
        </div>

        {/* Right Toolbar (Diagnostic tools) */}
        <div className="w-64 bg-gray-950 border-r border-gray-800 p-4 flex flex-col gap-4 text-gray-200 text-xs overflow-y-auto" dir="rtl">
          {/* Presets (Windowing) */}
          <div>
            <p className="font-bold text-gray-400 mb-2 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-teal-400" />
              نوافذ الفحص السريري (Windowing):
            </p>
            <div className="grid grid-cols-2 gap-1.5">
              {[
                { key: 'DEFAULT', label: 'افتراضي (Normal)' },
                { key: 'BONE', label: 'نافذة العظام (Bone)' },
                { key: 'SOFT_TISSUE', label: 'الأنسجة (Tissue)' },
                { key: 'LUNG', label: 'نافذة الرئة (Lung)' },
              ].map((w) => (
                <button
                  key={w.key}
                  type="button"
                  onClick={() => handlePresetChange(w.key as any)}
                  className={`p-2 rounded-xl border text-[11px] font-bold transition-all text-center ${
                    preset === w.key
                      ? 'bg-teal-500/20 border-teal-500 text-teal-300 shadow-sm'
                      : 'bg-gray-900 border-gray-800 text-gray-400 hover:bg-gray-800 hover:text-white'
                  }`}
                >
                  {w.label}
                </button>
              ))}
            </div>
          </div>

          {/* Zoom Controls */}
          <div>
            <p className="font-bold text-gray-400 mb-2 flex items-center gap-1.5">
              <ZoomIn className="w-3.5 h-3.5 text-primary-400" />
              التكبير والموضع:
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setZoom((z) => Math.min(z + 0.25, 4.5))}
                className="flex-1 p-2 rounded-xl bg-gray-900 hover:bg-gray-800 border border-gray-800 flex items-center justify-center gap-1 text-white transition-colors"
                title="تكبير"
              >
                <ZoomIn className="w-4 h-4" />
                <span>+</span>
              </button>
              <button
                onClick={() => setZoom((z) => Math.max(z - 0.25, 0.5))}
                className="flex-1 p-2 rounded-xl bg-gray-900 hover:bg-gray-800 border border-gray-800 flex items-center justify-center gap-1 text-white transition-colors"
                title="تصغير"
              >
                <ZoomOut className="w-4 h-4" />
                <span>-</span>
              </button>
              <button
                onClick={() => { setZoom(1); setPosition({ x: 0, y: 0 }); }}
                className="p-2 rounded-xl bg-gray-900 hover:bg-gray-800 border border-gray-800 text-gray-400 hover:text-white transition-colors"
                title="ملاءمة الشاشة"
              >
                <ResetIcon className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Rotation & Flip */}
          <div>
            <p className="font-bold text-gray-400 mb-2">التدوير والانعكاس:</p>
            <div className="grid grid-cols-4 gap-1.5">
              <button
                onClick={() => setRotation((r) => (r - 90 + 360) % 360)}
                className="p-2 rounded-xl bg-gray-900 hover:bg-gray-800 border border-gray-800 flex items-center justify-center text-gray-300 hover:text-white"
                title="تدوير 90 درجة يسار"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
              <button
                onClick={() => setRotation((r) => (r + 90) % 360)}
                className="p-2 rounded-xl bg-gray-900 hover:bg-gray-800 border border-gray-800 flex items-center justify-center text-gray-300 hover:text-white"
                title="تدوير 90 درجة يمين"
              >
                <RotateCw className="w-4 h-4" />
              </button>
              <button
                onClick={() => setFlipH(!flipH)}
                className={`p-2 rounded-xl border flex items-center justify-center transition-colors ${
                  flipH ? 'bg-teal-500/20 border-teal-500 text-teal-300' : 'bg-gray-900 border-gray-800 text-gray-300 hover:bg-gray-800'
                }`}
                title="انعكاس أفقي"
              >
                <FlipHorizontal className="w-4 h-4" />
              </button>
              <button
                onClick={() => setFlipV(!flipV)}
                className={`p-2 rounded-xl border flex items-center justify-center transition-colors ${
                  flipV ? 'bg-teal-500/20 border-teal-500 text-teal-300' : 'bg-gray-900 border-gray-800 text-gray-300 hover:bg-gray-800'
                }`}
                title="انعكاس رأسي"
              >
                <FlipVertical className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Caliper Tool Toggle */}
          <div>
            <p className="font-bold text-gray-400 mb-2 flex items-center gap-1.5">
              <Ruler className="w-3.5 h-3.5 text-teal-400" />
              أداة قياس الأبعاد (Caliper):
            </p>
            <button
              type="button"
              onClick={() => {
                const next = !rulerActive;
                setRulerActive(next);
                if (next) toast('انقر واسحب لقياس المسافة بالمليمتر');
              }}
              className={`w-full p-2.5 rounded-xl border flex items-center justify-center gap-2 font-bold transition-all cursor-pointer ${
                rulerActive
                  ? 'bg-teal-600 text-white border-teal-500 shadow-lg shadow-teal-500/30'
                  : 'bg-gray-900 hover:bg-gray-800 border-gray-800 text-gray-300'
              }`}
            >
              <Ruler className="w-4 h-4" />
              <span>{rulerActive ? 'أداة القياس نشطة (إلغاء)' : 'تفعيل أداة المسطرة السريرية'}</span>
            </button>
          </div>

          {/* Invert Colors (Negative) */}
          <div>
            <button
              type="button"
              onClick={() => setInvert(!invert)}
              className={`w-full p-2.5 rounded-xl border flex items-center justify-center gap-2 font-bold transition-all ${
                invert
                  ? 'bg-amber-500/20 border-amber-500 text-amber-300'
                  : 'bg-gray-900 hover:bg-gray-800 border-gray-800 text-gray-300'
              }`}
            >
              {invert ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              <span>{invert ? 'عكس الألوان نشط (Negative)' : 'عكس ألوان الصورة (Negative Mode)'}</span>
            </button>
          </div>

          {/* Brightness & Contrast sliders */}
          <div className="space-y-3 pt-2 border-t border-gray-800">
            <div>
              <div className="flex justify-between items-center mb-1 text-[11px] text-gray-400">
                <span className="flex items-center gap-1">
                  <Sun className="w-3 h-3 text-amber-400" />
                  السطوع:
                </span>
                <span className="font-mono">{brightness}%</span>
              </div>
              <input
                type="range"
                min="50"
                max="200"
                value={brightness}
                onChange={(e) => setBrightness(Number(e.target.value))}
                className="w-full h-1.5 bg-gray-800 rounded-lg appearance-none cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between items-center mb-1 text-[11px] text-gray-400">
                <span className="flex items-center gap-1">
                  <Contrast className="w-3 h-3 text-indigo-400" />
                  التباين:
                </span>
                <span className="font-mono">{contrast}%</span>
              </div>
              <input
                type="range"
                min="50"
                max="250"
                value={contrast}
                onChange={(e) => setContrast(Number(e.target.value))}
                className="w-full h-1.5 bg-gray-800 rounded-lg appearance-none cursor-pointer"
              />
            </div>
          </div>

          {/* Reset button */}
          <div className="mt-auto pt-4 border-t border-gray-800">
            <button
              onClick={handleReset}
              className="w-full py-2.5 rounded-xl border border-gray-800 hover:bg-gray-800 text-gray-400 hover:text-white font-medium text-xs flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
            >
              <ResetIcon className="w-3.5 h-3.5" />
              إعادة ضبط جميع المؤشرات
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
