import {
  type Announcements,
  DndContext,
  type DragEndEvent,
  KeyboardSensor,
  type Modifier,
  MouseSensor,
  TouchSensor,
  type UniqueIdentifier,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { ReactNode } from "react";
import { moveFor } from "../../lib/task-list.ts";
import { Icon } from "./icon.tsx";

/** Anything the list can order: it only needs a stable string id. */
export interface Sortable {
  readonly id: string;
}

/** Props for `SortableList`. */
export interface SortableListProps<T extends Sortable> {
  readonly items: readonly T[];
  readonly label: string;
  readonly itemLabel: (item: T) => string;
  readonly onMove: (id: string, afterId: string | null) => void;
  readonly children: (item: T, handle: ReactNode) => ReactNode;
  readonly disabled?: boolean;
  readonly className?: string;
  readonly itemClassName?: string;
}

const verticalOnly: Modifier = ({ transform }) => ({ ...transform, x: 0 });

const instructions = {
  draggable:
    "To move an item, press Space or Enter on its handle. Use the up and down arrow keys to move it, then press Space or Enter to drop it, or Escape to cancel.",
};

const announcementsFor = (
  ids: readonly string[],
  nameOf: (id: UniqueIdentifier) => string,
): Announcements => {
  const at = (id: UniqueIdentifier) =>
    `position ${String(ids.indexOf(String(id)) + 1)} of ${String(ids.length)}`;
  return {
    onDragStart: ({ active }) => `Picked up ${nameOf(active.id)}, at ${at(active.id)}.`,
    onDragOver: ({ active, over }) =>
      over
        ? `${nameOf(active.id)} is now at ${at(over.id)}.`
        : `${nameOf(active.id)} is outside the list.`,
    onDragEnd: ({ active, over }) =>
      over ? `Dropped ${nameOf(active.id)} at ${at(over.id)}.` : `Dropped ${nameOf(active.id)}.`,
    onDragCancel: ({ active }) =>
      `Move cancelled. ${nameOf(active.id)} is back at ${at(active.id)}.`,
  };
};

/**
 * A list the user reorders by mouse, touch (press and hold the handle) or keyboard.
 * It reports each move as `onMove(id, afterId)`, with `afterId` null for the top, and leaves the order to its owner.
 */
export function SortableList<T extends Sortable>({
  items,
  label,
  itemLabel,
  onMove,
  children,
  disabled = false,
  className = "",
  itemClassName = "",
}: SortableListProps<T>) {
  const sensors = useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: 4 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 150, tolerance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
  const ids = items.map((item) => item.id);
  const byId = new Map(items.map((item) => [item.id, item]));
  const nameOf = (id: UniqueIdentifier) => {
    const item = byId.get(String(id));
    return item ? itemLabel(item) : "item";
  };
  const handleDragEnd = ({ active, over }: DragEndEvent) => {
    const move = over ? moveFor(ids, String(active.id), String(over.id)) : null;
    if (move) onMove(move.taskId, move.afterId);
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      modifiers={[verticalOnly]}
      accessibility={{
        announcements: announcementsFor(ids, nameOf),
        screenReaderInstructions: instructions,
      }}
      onDragEnd={handleDragEnd}
    >
      <SortableContext items={ids} strategy={verticalListSortingStrategy} disabled={disabled}>
        <ul aria-label={label} className={className}>
          {items.map((item) => (
            <SortableItem
              key={item.id}
              item={item}
              name={itemLabel(item)}
              disabled={disabled}
              className={itemClassName}
              render={children}
            />
          ))}
        </ul>
      </SortableContext>
    </DndContext>
  );
}

interface SortableItemProps<T extends Sortable> {
  readonly item: T;
  readonly name: string;
  readonly disabled: boolean;
  readonly className: string;
  readonly render: (item: T, handle: ReactNode) => ReactNode;
}

function SortableItem<T extends Sortable>({
  item,
  name,
  disabled,
  className,
  render,
}: SortableItemProps<T>) {
  const {
    attributes,
    listeners,
    setNodeRef,
    setActivatorNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: item.id, disabled });
  const handle = disabled ? null : (
    <button
      type="button"
      ref={setActivatorNodeRef}
      {...attributes}
      {...listeners}
      aria-label={`Move ${name}`}
      className="flex size-touch shrink-0 cursor-grab touch-none items-center justify-center text-ink-muted transition-colors hover:text-ink active:cursor-grabbing"
    >
      <Icon name="grip" />
    </button>
  );
  return (
    <li
      ref={setNodeRef}
      data-dragging={isDragging || undefined}
      style={{
        transform: CSS.Translate.toString(transform),
        transition: transition ? "transform var(--duration-base) var(--ease-standard)" : undefined,
      }}
      className={className}
    >
      {render(item, handle)}
    </li>
  );
}
