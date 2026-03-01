/**
 * TableChipStack — renders a visual stack of casino chips representing a bet amount.
 */

const CHIPS = [
  { val: 0.5, label: '.50',  cls: 'chip-0-5'  },
  { val: 1,   label: '$1',   cls: 'chip-1'    },
  { val: 5,   label: '$5',   cls: 'chip-5'    },
  { val: 25,  label: '$25',  cls: 'chip-25'   },
  { val: 100, label: '$100', cls: 'chip-100'  },
  { val: 500, label: '$500', cls: 'chip-500'  },
];

const TABLE_CHIP_DENOMS = [...CHIPS]
  .map((chip) => ({
    ...chip,
    cents: Math.round(chip.val * 100),
  }))
  .sort((a, b) => b.cents - a.cents);

function breakdownBetIntoChips(amount = 0) {
  let remaining = Math.max(0, Math.round(amount * 100));
  const stacks = [];

  TABLE_CHIP_DENOMS.forEach((chip) => {
    if (remaining <= 0) return;
    const count = Math.floor(remaining / chip.cents);
    if (count > 0) {
      stacks.push({ ...chip, count });
      remaining -= count * chip.cents;
    }
  });

  if (remaining > 0) {
    const smallest = TABLE_CHIP_DENOMS[TABLE_CHIP_DENOMS.length - 1];
    const fallback = Math.ceil(remaining / smallest.cents);
    const existing = stacks.find((stack) => stack.cents === smallest.cents);
    if (existing) existing.count += fallback;
    else stacks.push({ ...smallest, count: fallback });
  }

  return stacks;
}

export default function TableChipStack({ amount }) {
  if (!amount || amount <= 0) return null;
  const dynamicStacks = breakdownBetIntoChips(amount);
  const countByCents = new Map(dynamicStacks.map((stack) => [stack.cents, stack.count]));
  const stacks = TABLE_CHIP_DENOMS.map((chip) => ({
    ...chip,
    count: countByCents.get(chip.cents) ?? 0,
  }));

  return (
    <div className="table-chip-stack" aria-label={`Current bet ${amount.toFixed(2)}`}>
      {stacks.map((stack) => {
        const visible = Math.min(stack.count, 8);
        return (
          <div
            className={`chip-stack-pile${stack.count === 0 ? ' is-empty' : ''}`}
            key={stack.cents}
          >
            {Array.from({ length: visible }).map((_, i) => (
              <div
                key={`${stack.cents}-${i}`}
                className={`table-chip ${stack.cls}`}
                style={{
                  '--chip-level': i,
                  '--chip-tilt': '0deg',
                }}
              />
            ))}
            {stack.count > visible && (
              <span className="chip-stack-count">x{stack.count}</span>
            )}
          </div>
        );
      })}
      <span className="table-chip-total">${amount.toFixed(2)}</span>
    </div>
  );
}

export { CHIPS, TABLE_CHIP_DENOMS };
