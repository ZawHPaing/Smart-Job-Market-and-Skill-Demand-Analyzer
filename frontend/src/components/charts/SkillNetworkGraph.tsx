import { useMemo, useEffect, useRef } from 'react';

interface NetworkNode {
  id: string;
  name: string;
  value: number;
  group: string;
  x?: number;
  y?: number;
}

interface NetworkLink {
  source: string;
  target: string;
  value: number;
}

interface SkillNetworkGraphProps {
  nodes: NetworkNode[];
  links: NetworkLink[];
  width?: number;
  height?: number;
  centerNode?: string;
}

export function SkillNetworkGraph({
  nodes,
  links,
  width = 400,
  height = 400,
  centerNode,
}: SkillNetworkGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  const { positionedNodes, positionedLinks } = useMemo(() => {
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) * 0.35;

    // Position nodes in a circle, with center node in the middle
    const sortedNodes = [...nodes].sort((a, b) => {
      if (centerNode) {
        if (a.id === centerNode) return -1;
        if (b.id === centerNode) return 1;
      }
      return b.value - a.value;
    });

    const positioned = sortedNodes.map((node, index) => {
      if (centerNode && node.id === centerNode) {
        return { ...node, x: centerX, y: centerY };
      }
      const adjustedIndex = centerNode ? index - 1 : index;
      const totalNodes = centerNode ? sortedNodes.length - 1 : sortedNodes.length;
      const angle = (adjustedIndex / totalNodes) * 2 * Math.PI - Math.PI / 2;
      return {
        ...node,
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      };
    });

    const nodeMap = new Map(positioned.map((n) => [n.id, n]));
    
    const posLinks = links.map((link) => ({
      ...link,
      sourceNode: nodeMap.get(link.source),
      targetNode: nodeMap.get(link.target),
    })).filter(l => l.sourceNode && l.targetNode);

    return { positionedNodes: positioned, positionedLinks: posLinks };
  }, [nodes, links, width, height, centerNode]);

  const getNodeColor = (group: string) => {
    const colors: Record<string, string> = {
      tech: 'hsl(186 100% 50%)',
      soft: 'hsl(258 90% 76%)',
      general: 'hsl(142 76% 45%)',
    };
    return colors[group] || 'hsl(0 0% 65%)';
  };

  return (
    <svg
      ref={svgRef}
      width={width}
      height={height}
      className="overflow-visible"
      viewBox={`0 0 ${width} ${height}`}
    >
      {/* Links */}
      <g>
        {positionedLinks.map((link, index) => (
          <line
            key={`link-${index}`}
            x1={link.sourceNode?.x}
            y1={link.sourceNode?.y}
            x2={link.targetNode?.x}
            y2={link.targetNode?.y}
            stroke="hsl(0 0% 30%)"
            strokeWidth={Math.max(1, link.value / 3)}
            strokeOpacity={0.6}
            className="transition-all duration-300 hover:stroke-cyan hover:stroke-opacity-100"
          />
        ))}
      </g>

      {/* Nodes */}
      <g>
        {positionedNodes.map((node) => {
          const nodeRadius = Math.max(8, Math.sqrt(node.value) * 1.5);
          const isCenter = centerNode && node.id === centerNode;

          return (
            <g
              key={node.id}
              className="cursor-pointer transition-transform duration-200 hover:scale-110"
              style={{ transformOrigin: `${node.x}px ${node.y}px` }}
            >
              {/* Glow effect for center node */}
              {isCenter && (
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={nodeRadius + 10}
                  fill="none"
                  stroke={getNodeColor(node.group)}
                  strokeWidth={2}
                  strokeOpacity={0.3}
                  className="animate-glow-pulse"
                />
              )}
              <circle
                cx={node.x}
                cy={node.y}
                r={nodeRadius}
                fill={getNodeColor(node.group)}
                stroke="hsl(0 0% 10%)"
                strokeWidth={2}
                className="transition-all duration-300"
              />
              <text
                x={node.x}
                y={node.y! + nodeRadius + 14}
                textAnchor="middle"
                fill="hsl(0 0% 80%)"
                fontSize={isCenter ? 12 : 10}
                fontWeight={isCenter ? 600 : 400}
                className="select-none"
              >
                {node.name}
              </text>
            </g>
          );
        })}
      </g>
    </svg>
  );
}
