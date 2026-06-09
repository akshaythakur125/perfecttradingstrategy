import React from 'react';
import { Card, CardTitle } from '../common/Card';

export function RiskRules() {
  return (
    <Card>
      <CardTitle className="text-lg font-semibold mb-4">Risk Management Rules</CardTitle>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        <div className="space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Risk Per Trade</span>
            <span className="font-mono">1%</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Max Open Positions</span>
            <span className="font-mono">3</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Daily Loss Limit</span>
            <span className="font-mono">3%</span>
          </div>
        </div>
        <div className="space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Weekly Loss Limit</span>
            <span className="font-mono">8%</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Min Risk/Reward</span>
            <span className="font-mono">1:3</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Position Sizing</span>
            <span className="font-mono">Dynamic (ATR)</span>
          </div>
        </div>
      </div>
    </Card>
  );
}
